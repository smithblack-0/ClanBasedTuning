"""Ray contract for winner-only checkpoint publication and native reassignment."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
ray = pytest.importorskip("ray")

from ray import tune  # noqa: E402
from ray.tune.schedulers import FIFOScheduler, TrialScheduler  # noqa: E402


def _append_event(audit_path, event):
    with Path(audit_path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


class _StatefulMember(tune.Trainable):
    """Expose observable class-Trainable save, restore, and reset behavior."""

    def setup(self, config):
        self.model_value = 10.0
        self.source_member = None
        _append_event(
            config["audit_path"],
            {
                "event": "setup",
                "member_id": config["member_id"],
                "lr": config["lr"],
                "round_index": config["round_index"],
            },
        )

    def step(self):
        self.model_value -= self.config["lr"]
        _append_event(
            self.config["audit_path"],
            {
                "event": "step",
                "member_id": self.config["member_id"],
                "lr": self.config["lr"],
                "model_value": self.model_value,
                "restored_from": self.source_member,
                "round_index": self.config["round_index"],
            },
        )
        return {
            "member_id": self.config["member_id"],
            "round_index": self.config["round_index"],
            "fitness": (
                [3.0, 1.0, 2.0][self.config["member_id"]]
                if self.config["round_index"] == 0
                else self.model_value
            ),
        }

    def save_checkpoint(self, checkpoint_dir):
        _append_event(
            self.config["audit_path"],
            {
                "event": "save",
                "member_id": self.config["member_id"],
                "round_index": self.config["round_index"],
            },
        )
        checkpoint_path = Path(checkpoint_dir) / "member_state.json"
        checkpoint_path.write_text(
            json.dumps(
                {
                    "model_value": self.model_value,
                    "source_member": self.config["member_id"],
                }
            ),
            encoding="utf-8",
        )
        return checkpoint_dir

    def load_checkpoint(self, checkpoint_dir):
        state = json.loads((Path(checkpoint_dir) / "member_state.json").read_text(encoding="utf-8"))
        self.model_value = state["model_value"]
        self.source_member = state["source_member"]
        _append_event(
            self.config["audit_path"],
            {
                "event": "load",
                "member_id": self.config["member_id"],
                "lr": self.config["lr"],
                "restored_from": self.source_member,
                "round_index": self.config["round_index"],
            },
        )


class _WinnerOnlyScheduler(FIFOScheduler):
    """Hold one population, save its sole winner, and assign that checkpoint."""

    _supports_buffered_results = False

    def __init__(self, population_size):
        super().__init__()
        self.population_size = population_size
        self.results = {}
        self.transitions = []

    def on_trial_result(self, tune_controller, trial, result):
        round_index = result["round_index"]
        round_results = self.results.setdefault(round_index, {})
        member_id = result["member_id"]
        if member_id in round_results:
            raise RuntimeError(f"member {member_id} reported round {round_index} twice")
        round_results[member_id] = (trial, dict(result))

        if len(round_results) < self.population_size:
            return TrialScheduler.NOOP

        if round_index == 1:
            tune_controller.request_stop_experiment()
            return TrialScheduler.NOOP

        winner_id = min(
            round_results,
            key=lambda candidate: (round_results[candidate][1]["fitness"], candidate),
        )
        winner_trial, winner_result = round_results[winner_id]
        checkpoint_future = tune_controller._schedule_trial_save(
            winner_trial,
            result=winner_result,
        )
        winner_checkpoint = checkpoint_future.resolve()
        if winner_checkpoint is None or winner_checkpoint.checkpoint is None:
            raise RuntimeError("winner did not produce an assignable checkpoint")

        next_learning_rates = {}
        for target_id, (target_trial, _) in sorted(round_results.items()):
            next_config = dict(target_trial.config)
            next_config["round_index"] = round_index + 1
            next_config["lr"] = 0.2 if target_id == winner_id else 0.2 + 0.01 * (target_id + 1)
            next_learning_rates[target_id] = next_config["lr"]

            if target_trial.status == target_trial.RUNNING:
                tune_controller.pause_trial(target_trial, should_checkpoint=False)
            target_trial.set_config(next_config)
            target_trial.run_metadata.checkpoint_manager._latest_checkpoint_result = copy.copy(
                winner_checkpoint
            )

        self.transitions.append(
            {
                "round_index": round_index,
                "winner_id": winner_id,
                "next_learning_rates": next_learning_rates,
            }
        )
        return TrialScheduler.NOOP


def test_ray_saves_only_winner_then_restores_every_target(tmp_path):
    scheduler = _WinnerOnlyScheduler(population_size=3)
    audit_path = tmp_path / "events.jsonl"
    ray.init(num_cpus=3, include_dashboard=False, ignore_reinit_error=True)
    try:
        tuner = tune.Tuner(
            tune.with_resources(_StatefulMember, {"cpu": 1}),
            param_space={
                "member_id": tune.grid_search([0, 1, 2]),
                "lr": tune.sample_from(lambda config: 0.1 * (config["member_id"] + 1)),
                "round_index": 0,
                "audit_path": str(audit_path),
            },
            run_config=tune.RunConfig(
                storage_path=str(tmp_path / "ray-results"),
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
    assert scheduler.transitions[0]["round_index"] == 0
    assert scheduler.transitions[0]["winner_id"] == 1
    assert scheduler.transitions[0]["next_learning_rates"] == pytest.approx(
        {0: 0.21, 1: 0.2, 2: 0.23}
    )

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
    assert {event["lr"] for event in second_round_steps} == {0.2, 0.21, 0.23}
