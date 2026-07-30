"""Ray contract for winner-only checkpoint publication and native reassignment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
ray = pytest.importorskip("ray")

from ray import tune  # noqa: E402

from clan_based_tuning.ray import (  # noqa: E402
    CLAN_MEMBER_ID,
    CLAN_NEXT_CONFIG,
    CLAN_ROUND_INDEX,
    CLAN_WINNER_ID,
    ClanTransitionScheduler,
)


def _append_event(audit_path, event):
    with Path(audit_path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


class _StatefulMember(tune.Trainable):
    """Expose observable class-Trainable save, restore, and reset behavior."""

    def setup(self, config):
        self.model_value = 10.0
        self.optimizer_velocity = 0.0
        self.source_member = None
        _append_event(
            config["audit_path"],
            {
                "event": "setup",
                "member_id": config[CLAN_MEMBER_ID],
                "lr": config["lr"],
                "round_index": config[CLAN_ROUND_INDEX],
            },
        )

    def step(self):
        self.optimizer_velocity = 0.9 * self.optimizer_velocity + 1.0
        self.model_value -= self.config["lr"] * self.optimizer_velocity
        _append_event(
            self.config["audit_path"],
            {
                "event": "step",
                "member_id": self.config[CLAN_MEMBER_ID],
                "lr": self.config["lr"],
                "model_value": self.model_value,
                "optimizer_velocity": self.optimizer_velocity,
                "restored_from": self.source_member,
                "round_index": self.config[CLAN_ROUND_INDEX],
            },
        )
        return {
            CLAN_MEMBER_ID: self.config[CLAN_MEMBER_ID],
            CLAN_ROUND_INDEX: self.config[CLAN_ROUND_INDEX],
            CLAN_WINNER_ID: 1,
            CLAN_NEXT_CONFIG: {
                "lr": (
                    0.2
                    if self.config[CLAN_MEMBER_ID] == 1
                    else 0.2 + 0.01 * (self.config[CLAN_MEMBER_ID] + 1)
                )
            },
            "round_index": self.config[CLAN_ROUND_INDEX],
            "fitness": (
                [3.0, 1.0, 2.0][self.config[CLAN_MEMBER_ID]]
                if self.config[CLAN_ROUND_INDEX] == 0
                else self.model_value
            ),
        }

    def save_checkpoint(self, checkpoint_dir):
        _append_event(
            self.config["audit_path"],
            {
                "event": "save",
                "member_id": self.config[CLAN_MEMBER_ID],
                "round_index": self.config[CLAN_ROUND_INDEX],
            },
        )
        checkpoint_path = Path(checkpoint_dir) / "member_state.json"
        checkpoint_path.write_text(
            json.dumps(
                {
                    "model_value": self.model_value,
                    "optimizer_velocity": self.optimizer_velocity,
                    "source_member": self.config[CLAN_MEMBER_ID],
                }
            ),
            encoding="utf-8",
        )
        return checkpoint_dir

    def load_checkpoint(self, checkpoint_dir):
        state = json.loads((Path(checkpoint_dir) / "member_state.json").read_text(encoding="utf-8"))
        self.model_value = state["model_value"]
        self.optimizer_velocity = state["optimizer_velocity"]
        self.source_member = state["source_member"]
        _append_event(
            self.config["audit_path"],
            {
                "event": "load",
                "member_id": self.config[CLAN_MEMBER_ID],
                "lr": self.config["lr"],
                "restored_from": self.source_member,
                "round_index": self.config[CLAN_ROUND_INDEX],
            },
        )


class _TrialStub:
    def __init__(self, member_id, round_index=0):
        self.config = {
            CLAN_MEMBER_ID: member_id,
            CLAN_ROUND_INDEX: round_index,
        }


def _reported_transition(member_id, winner_id, *, round_index=0):
    return {
        CLAN_MEMBER_ID: member_id,
        CLAN_ROUND_INDEX: round_index,
        CLAN_WINNER_ID: winner_id,
        f"{CLAN_NEXT_CONFIG}/lr": 0.1 * (member_id + 1),
    }


def test_scheduler_rejects_process_disagreement_before_checkpointing():
    scheduler = ClanTransitionScheduler(population_size=3)
    scheduler.on_trial_result(None, _TrialStub(0), _reported_transition(0, 1))
    scheduler.on_trial_result(None, _TrialStub(1), _reported_transition(1, 1))

    with pytest.raises(RuntimeError, match="disagree"):
        scheduler.on_trial_result(None, _TrialStub(2), _reported_transition(2, 0))


def test_scheduler_rejects_a_duplicate_process_report():
    scheduler = ClanTransitionScheduler(population_size=3)
    scheduler.on_trial_result(None, _TrialStub(0), _reported_transition(0, 1))

    with pytest.raises(RuntimeError, match="reported round 0 twice"):
        scheduler.on_trial_result(None, _TrialStub(0), _reported_transition(0, 1))


def test_scheduler_rejects_a_process_from_the_wrong_round():
    scheduler = ClanTransitionScheduler(population_size=3)

    with pytest.raises(RuntimeError, match="expected Clan round 0"):
        scheduler.on_trial_result(
            None,
            _TrialStub(0, round_index=1),
            _reported_transition(0, 1, round_index=1),
        )


def test_ray_saves_only_winner_then_restores_every_target(tmp_path):
    scheduler = ClanTransitionScheduler(population_size=3)
    audit_path = tmp_path / "events.jsonl"
    ray.init(num_cpus=3, include_dashboard=False, ignore_reinit_error=True)
    try:
        tuner = tune.Tuner(
            tune.with_resources(_StatefulMember, {"cpu": 1}),
            param_space={
                CLAN_MEMBER_ID: tune.grid_search([0, 1, 2]),
                "lr": tune.sample_from(lambda config: 0.1 * (config[CLAN_MEMBER_ID] + 1)),
                CLAN_ROUND_INDEX: 0,
                "audit_path": str(audit_path),
            },
            run_config=tune.RunConfig(
                storage_path=str(tmp_path / "ray-results"),
                stop={"training_iteration": 2},
                checkpoint_config=tune.CheckpointConfig(
                    checkpoint_frequency=0,
                    checkpoint_at_end=False,
                ),
                failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
                verbose=0,
            ),
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                max_concurrent_trials=3,
                reuse_actors=False,
            ),
        )
        result_grid = tuner.fit()
    finally:
        ray.shutdown()

    assert not [result.error for result in result_grid if result.error is not None]
    events = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line
    ]
    saves = [event for event in events if event["event"] == "save"]
    assert saves == [{"event": "save", "member_id": 1, "round_index": 0}]

    second_round_steps = [
        event for event in events if event["event"] == "step" and event["round_index"] == 1
    ]
    assert len(second_round_steps) == 3
    assert {event["member_id"] for event in second_round_steps} == {0, 1, 2}
    assert {event["restored_from"] for event in second_round_steps} == {1}
    assert {event["optimizer_velocity"] for event in second_round_steps} == {1.9}
    assert sorted(event["lr"] for event in second_round_steps) == pytest.approx([0.2, 0.21, 0.23])
