"""Ray 2.56 contract for the winner-only Clan transition seam."""

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("ray")

from ray.train import Checkpoint
from ray.train._internal.session import _FutureTrainingResult, _TrainingResult
from ray.tune.experiment import Trial
from ray.tune.schedulers import TrialScheduler
from ray.tune.utils.util import flatten_dict

from clan_based_tuning import ClanController, ClanRound, MutationSpec
from clan_based_tuning.ray_transition import (
    CONTROLLER_STATE,
    MEMBER_ID,
    NEXT_MEMBER_STATE,
    OPTIMIZER_CONFIG,
    ClanTrialScheduler,
    MemberTransition,
)


class FakeFuture(_FutureTrainingResult):
    def __init__(self, result):
        self._result = result

    def resolve(self, block=True):
        return self._result


class FakeTuneController:
    """Expose the exact TuneController effects used by the integration."""

    def __init__(self, checkpoint_directory):
        self.trials = []
        self.checkpoint_directory = checkpoint_directory
        self.save_calls = []
        self.pause_calls = []

    def get_trials(self):
        return self.trials

    def _schedule_trial_save(self, trial, result=None):
        self.save_calls.append(trial.config[MEMBER_ID])
        checkpoint = Checkpoint.from_directory(self.checkpoint_directory)
        return FakeFuture(_TrainingResult(checkpoint=checkpoint, metrics=result))

    def pause_trial(self, trial, should_checkpoint=True):
        self.pause_calls.append((trial.config[MEMBER_ID], should_checkpoint))
        trial.set_status(Trial.PAUSED)


def _trial(member_id, tune_controller):
    trial = Trial(
        "__fake",
        config={MEMBER_ID: member_id},
        trial_id=f"member_{member_id}",
        stub=True,
    )
    trial.set_status(Trial.RUNNING)
    tune_controller.trials.append(trial)
    return trial


def _result(member_id, winner_id, optimizer_config):
    return flatten_dict(
        MemberTransition(
            round_index=0,
            member_id=member_id,
            winner_id=winner_id,
            fitness=[4.0, 1.0][member_id],
            controller_state={
                "round_index": 1,
                "member_state": f"member-{member_id}",
            },
            optimizer_config=optimizer_config,
        ).as_result()
    )


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_member_transition_captures_the_advanced_process_local_controller():
    winner_calls = []
    completed_population = [
        ClanRound(0, 0, {"lr": 1.0}, lambda round_: None, 1.0),
        ClanRound(1, 0, {"lr": 2.0}, lambda round_: None, 2.0),
    ]
    controller = ClanController(
        member_id=0,
        population_size=2,
        initial_config={"lr": 1.0},
        mutations={
            "lr": MutationSpec(
                standard_deviation=0.0,
                geometry="linear",
                minimum=0.0,
                maximum=10.0,
            )
        },
        mode="min",
        seed=7,
        save_member_fitness=lambda round_: None,
        load_population=lambda round_index: completed_population,
        select_winner=winner_calls.append,
    )
    controller.set_fitness(1.0)
    controller.advance()

    transition = MemberTransition.from_controller(
        completed_round_index=0,
        fitness=1.0,
        winner_id=winner_calls[0],
        controller=controller,
    )

    assert transition.member_id == 0
    assert transition.winner_id == 0
    assert transition.controller_state["round_index"] == 1
    assert transition.optimizer_config == {"lr": 1.0}


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_complete_round_saves_only_winner_and_assigns_local_next_state():
    """The Ray seam shares one checkpoint without erasing member-local state."""

    scheduler = ClanTrialScheduler()
    with tempfile.TemporaryDirectory() as checkpoint_directory:
        Path(checkpoint_directory, "winner-state").write_text("member 1")
        tune_controller = FakeTuneController(checkpoint_directory)
        trials = [_trial(member_id, tune_controller) for member_id in range(2)]

        first = scheduler.on_trial_result(
            tune_controller,
            trials[0],
            _result(0, 1, {"lr": 0.5}),
        )
        assert first == TrialScheduler.NOOP
        assert tune_controller.save_calls == []
        assert tune_controller.pause_calls == []

        last = scheduler.on_trial_result(
            tune_controller,
            trials[1],
            _result(1, 1, {"lr": 1.0}),
        )

        assert last == TrialScheduler.NOOP
        assert tune_controller.save_calls == [1]
        assert tune_controller.pause_calls == [(0, False), (1, False)]
        assert [trial.status for trial in trials] == [Trial.PAUSED, Trial.PAUSED]
        assert [trial.config[NEXT_MEMBER_STATE][OPTIMIZER_CONFIG] for trial in trials] == [
            {"lr": 0.5},
            {"lr": 1.0},
        ]
        assert [
            trial.config[NEXT_MEMBER_STATE][CONTROLLER_STATE]["member_state"] for trial in trials
        ] == ["member-0", "member-1"]
        assert {trial.latest_checkpoint_result.checkpoint.path for trial in trials} == {
            checkpoint_directory
        }


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_transition_rejects_controller_disagreement_before_checkpointing():
    scheduler = ClanTrialScheduler()
    with tempfile.TemporaryDirectory() as checkpoint_directory:
        tune_controller = FakeTuneController(checkpoint_directory)
        trials = [_trial(member_id, tune_controller) for member_id in range(2)]
        scheduler.on_trial_result(tune_controller, trials[0], _result(0, 0, {"lr": 0.5}))

        with pytest.raises(RuntimeError, match="disagree"):
            scheduler.on_trial_result(
                tune_controller,
                trials[1],
                _result(1, 1, {"lr": 1.0}),
            )

        assert tune_controller.save_calls == []
        assert tune_controller.pause_calls == []


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_scheduler_composes_with_an_independent_transition_function():
    applied_members = []

    def record_transition(tune_controller, arrivals):
        applied_members.append([arrival.transition.member_id for arrival in arrivals])

    scheduler = ClanTrialScheduler(apply_transition=record_transition)
    with tempfile.TemporaryDirectory() as checkpoint_directory:
        tune_controller = FakeTuneController(checkpoint_directory)
        trials = [_trial(member_id, tune_controller) for member_id in range(2)]
        scheduler.on_trial_result(tune_controller, trials[1], _result(1, 1, {"lr": 1.0}))
        scheduler.on_trial_result(tune_controller, trials[0], _result(0, 1, {"lr": 0.5}))

    assert applied_members == [[0, 1]]
    assert tune_controller.save_calls == []
    assert tune_controller.pause_calls == []


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_transition_rejects_duplicate_member_report():
    scheduler = ClanTrialScheduler()
    with tempfile.TemporaryDirectory() as checkpoint_directory:
        tune_controller = FakeTuneController(checkpoint_directory)
        trials = [_trial(member_id, tune_controller) for member_id in range(2)]
        result = _result(0, 1, {"lr": 0.5})
        scheduler.on_trial_result(tune_controller, trials[0], result)

        with pytest.raises(RuntimeError, match="same Clan round twice"):
            scheduler.on_trial_result(tune_controller, trials[0], result)


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_member_failure_invalidates_active_clan():
    scheduler = ClanTrialScheduler()
    with tempfile.TemporaryDirectory() as checkpoint_directory:
        tune_controller = FakeTuneController(checkpoint_directory)
        trial = _trial(0, tune_controller)

        with pytest.raises(RuntimeError, match="member 0 failed"):
            scheduler.on_trial_error(tune_controller, trial)
