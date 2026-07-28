"""Ray contract for invoking controllers beside stopped FunctionTrainable members.

This test qualifies one narrow Milestone 3 seam. It does not choose the production
scheduler, transfer checkpoints, resume a generation, or exercise Lightning or DDP.
"""

from __future__ import annotations

import os
from functools import partial

import pytest

from clan_based_tuning import ClanController, ClanRound, MutationSpec

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
ray = pytest.importorskip("ray")

from ray import tune  # noqa: E402
from ray.tune.schedulers import FIFOScheduler, TrialScheduler  # noqa: E402
from ray.tune.trainable.function_trainable import FunctionTrainable  # noqa: E402


def _unused_publish(round_):
    raise AssertionError(f"loaded population record was unexpectedly published: {round_}")


def _advance_process_local_controller(trainable, *, population):
    """Run one actor-local controller decision without calling Trainable.train()."""

    trainable.install_population(
        [
            ClanRound(
                member_id=record["member_id"],
                round_index=record["round_index"],
                config={"lr": record["learning_rate"]},
                save_member_fitness=_unused_publish,
                fitness=record["fitness"],
            )
            for record in population
        ]
    )
    iteration_before = trainable.training_iteration
    trainable.controller.advance()

    return {
        "actor_pid": os.getpid(),
        "member_id": trainable.member_id,
        "winner_id": trainable.selected_winner,
        "learning_rate": trainable.controller.get_config()["lr"],
        "round_index": trainable.controller.state_dict()["round_index"],
        "iteration_before": iteration_before,
        "iteration_after": trainable.training_iteration,
    }


class _ControllerFunctionTrainable(FunctionTrainable):
    """Expose one real process-local controller at a stopped Tune result boundary."""

    def setup(self, config):
        member = config["member"]
        self.member_id = member["member_id"]
        self._population = None
        self._published_round = None
        self.selected_winner = None
        self.controller = ClanController(
            member_id=self.member_id,
            population_size=2,
            initial_config={"lr": member["learning_rate"]},
            mutations={
                "lr": MutationSpec(
                    standard_deviation=0.0,
                    geometry="linear",
                    minimum=0.0,
                    maximum=10.0,
                )
            },
            mode="min",
            seed=17,
            save_member_fitness=self._publish_round,
            load_population=self._load_population,
            select_winner=self._select_winner,
        )
        super().setup(config)

    def _trainable_func(self, config):
        member = config["member"]
        self.controller.set_fitness(member["fitness"])
        tune.report(
            {
                "member_id": self.member_id,
                "round_index": self._published_round.round_index,
                "fitness": self._published_round.fitness,
                "learning_rate": self._published_round.get_config()["lr"],
            }
        )
        raise AssertionError("Tune resumed training before the probe stopped the Clan")

    def install_population(self, population):
        if self._population is not None:
            raise RuntimeError("decision population was installed more than once")
        self._population = population

    def _publish_round(self, round_):
        if self._published_round is not None:
            raise RuntimeError("member round was published more than once")
        self._published_round = round_

    def _load_population(self, round_index):
        if self._population is None:
            raise RuntimeError("decision population has not been installed")
        if any(round_.round_index != round_index for round_ in self._population):
            raise RuntimeError("decision population belongs to another round")
        return self._population

    def _select_winner(self, winner_id):
        if self.selected_winner is not None:
            raise RuntimeError("winner was selected more than once")
        self.selected_winner = winner_id


class _ControllerInvocationScheduler(FIFOScheduler):
    """Hold one result per member and dispatch exactly one tracked actor-local call."""

    _supports_buffered_results = False

    def __init__(self, population_size):
        super().__init__()
        self.population_size = population_size
        self.results = {}
        self.trials = {}
        self.decisions = {}
        self.task_errors = []
        self._dispatched = False
        self._tune_controller = None

    def on_trial_result(self, tune_controller, trial, result):
        member_id = result["member_id"]
        if member_id in self.results:
            raise RuntimeError(f"member {member_id} reported more than once")

        self._tune_controller = tune_controller
        self.trials[member_id] = trial
        self.results[member_id] = {
            "member_id": member_id,
            "round_index": result["round_index"],
            "fitness": result["fitness"],
            "learning_rate": result["learning_rate"],
            "actor_pid": result["pid"],
        }

        if len(self.results) == self.population_size:
            self._dispatch_controller_calls()
        return TrialScheduler.NOOP

    def _dispatch_controller_calls(self):
        if self._dispatched:
            raise RuntimeError("controller calls were dispatched more than once")
        self._dispatched = True
        population = tuple(self.results[index] for index in range(self.population_size))

        for member_id in range(self.population_size):
            trial = self.trials[member_id]
            self._tune_controller._schedule_trial_task(
                trial=trial,
                method_name="execute",
                args=(partial(_advance_process_local_controller, population=population),),
                on_result=self._record_decision,
                on_error=self._record_task_error,
            )

    def _record_decision(self, trial, decision):
        if trial.trial_id in self.decisions:
            raise RuntimeError(f"trial {trial.trial_id} returned two decisions")
        self.decisions[trial.trial_id] = decision
        if len(self.decisions) == self.population_size:
            self._tune_controller.request_stop_experiment()

    def _record_task_error(self, trial, error):
        self.task_errors.append((trial.trial_id, repr(error)))
        self._tune_controller.request_stop_experiment()


def test_tune_invokes_each_process_local_controller_without_advancing_training(tmp_path):
    """Every stopped member consumes one complete population at iteration one."""

    scheduler = _ControllerInvocationScheduler(population_size=2)
    ray.init(num_cpus=2, include_dashboard=False, ignore_reinit_error=True)
    try:
        tuner = tune.Tuner(
            tune.with_resources(_ControllerFunctionTrainable, {"cpu": 1}),
            param_space={
                "member": tune.grid_search(
                    [
                        {"member_id": 0, "fitness": 1.0, "learning_rate": 0.1},
                        {"member_id": 1, "fitness": 2.0, "learning_rate": 0.2},
                    ]
                )
            },
            run_config=tune.RunConfig(
                storage_path=str(tmp_path),
                failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
                verbose=0,
            ),
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                max_concurrent_trials=2,
                reuse_actors=False,
            ),
        )
        result_grid = tuner.fit()
    finally:
        ray.shutdown()

    assert not scheduler.task_errors
    assert len(scheduler.results) == len(scheduler.decisions) == 2
    assert not [result.error for result in result_grid if result.error is not None]

    report_pids = {result["actor_pid"] for result in scheduler.results.values()}
    decision_pids = {decision["actor_pid"] for decision in scheduler.decisions.values()}
    assert decision_pids == report_pids
    assert len(decision_pids) == 2

    decisions = sorted(scheduler.decisions.values(), key=lambda item: item["member_id"])
    assert [decision["winner_id"] for decision in decisions] == [0, 0]
    assert [decision["learning_rate"] for decision in decisions] == [0.1, 0.1]
    assert [decision["round_index"] for decision in decisions] == [1, 1]
    assert [decision["iteration_before"] for decision in decisions] == [1, 1]
    assert [decision["iteration_after"] for decision in decisions] == [1, 1]
