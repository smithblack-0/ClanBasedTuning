from __future__ import annotations

import os
import time
from collections.abc import Callable

import ray
from ray import tune
from ray.tune.experiment import Trial
from ray.tune.schedulers import FIFOScheduler, TrialScheduler
from ray.tune.search import BasicVariantGenerator


class ClanMemberAdmission:
    def __init__(self, train_member: Callable[[dict], None]):
        self._train_member = train_member

    def __call__(self, config):
        member = dict(config["clan_member"])
        identity = {
            "clan/member_id": member["member_id"],
            "clan/rank": member["rank"],
            "clan/world_size": member["world_size"],
            "clan/pid": os.getpid(),
        }
        tune.report({"clan/phase": "ready", **identity})
        tune.report({"clan/phase": "armed", **identity})
        return self._train_member(config)


class ClanPopulationAdmissionScheduler(TrialScheduler):
    _supports_buffered_results = False

    def __init__(self, *, ready_timeout_s=30.0, armed_timeout_s=30.0):
        super().__init__()
        self._downstream = FIFOScheduler()
        self._ready_timeout_s = ready_timeout_s
        self._armed_timeout_s = armed_timeout_s
        self.phase = "COLLECTING_READY"
        self.deadline = None
        self.trials = {}
        self.ready = {}
        self.armed = {}
        self.release_attempts = {"ready": [], "armed": []}
        self.errors = []

    def set_search_properties(self, metric, mode, **spec):
        if metric is not None or mode is not None:
            return False
        own = super().set_search_properties(metric, mode, **spec)
        child = self._downstream.set_search_properties(metric, mode, **spec)
        return own and child

    def on_trial_add(self, tune_controller, trial):
        if self.deadline is None:
            self.deadline = time.monotonic() + self._ready_timeout_s
        self.trials[trial.trial_id] = trial
        self._downstream.on_trial_add(tune_controller, trial)
        self._check_search(tune_controller)

    def on_trial_result(self, tune_controller, trial, result):
        phase = result.get("clan/phase")
        if self.phase == "COLLECTING_READY" and phase == "ready":
            assert trial.trial_id not in self.ready
            self.ready[trial.trial_id] = self._record(trial, result)
            self._progress(tune_controller)
            return TrialScheduler.NOOP
        if self.phase == "COLLECTING_ARMED" and phase == "armed":
            assert trial.trial_id not in self.armed
            self.armed[trial.trial_id] = self._record(trial, result)
            self._progress(tune_controller)
            return TrialScheduler.NOOP
        return self._downstream.on_trial_result(tune_controller, trial, result)

    def on_trial_error(self, tune_controller, trial):
        self.errors.append(("error", trial.trial_id))
        tune_controller.request_stop_experiment()
        self._downstream.on_trial_error(tune_controller, trial)

    def on_trial_complete(self, tune_controller, trial, result):
        self._downstream.on_trial_complete(tune_controller, trial, result)

    def on_trial_remove(self, tune_controller, trial):
        self.errors.append(("remove", trial.trial_id))
        tune_controller.request_stop_experiment()
        self._downstream.on_trial_remove(tune_controller, trial)

    def choose_trial_to_run(self, tune_controller):
        self._progress(tune_controller)
        return self._downstream.choose_trial_to_run(tune_controller)

    def debug_string(self):
        return f"admission={self.phase}; {self._downstream.debug_string()}"

    def save(self, checkpoint_path):
        raise NotImplementedError

    def restore(self, checkpoint_path):
        raise NotImplementedError

    def _record(self, trial, result):
        configured = dict(trial.config["clan_member"])
        assert result["clan/member_id"] == configured["member_id"]
        assert result["clan/rank"] == configured["rank"]
        assert result["clan/world_size"] == configured["world_size"]
        return {
            "member_id": result["clan/member_id"],
            "rank": result["clan/rank"],
            "world_size": result["clan/world_size"],
            "pid": result["clan/pid"],
        }

    def _check_search(self, tune_controller):
        search = tune_controller.search_alg
        assert type(search) is BasicVariantGenerator
        assert search.max_concurrent == 0
        assert search.total_samples >= 2

    def _progress(self, tune_controller):
        if self.phase in {"ACTIVE", "FAILED"}:
            return
        self._check_search(tune_controller)
        if time.monotonic() > self.deadline:
            self.phase = "FAILED"
            tune_controller.request_stop_experiment()
            return
        search = tune_controller.search_alg
        trials = tuple(sorted(tune_controller.get_trials(), key=lambda item: item.trial_id))
        if not search.is_finished() or len(trials) != search.total_samples:
            return
        if any(trial.status != Trial.RUNNING for trial in trials):
            return
        records = self.ready if self.phase == "COLLECTING_READY" else self.armed
        if set(records) != {trial.trial_id for trial in trials}:
            return
        count = search.total_samples
        assert {record["member_id"] for record in records.values()} == set(range(count))
        assert {record["rank"] for record in records.values()} == set(range(count))
        assert {record["world_size"] for record in records.values()} == {count}

        released_phase = "ready" if self.phase == "COLLECTING_READY" else "armed"
        self.phase = "COLLECTING_ARMED" if released_phase == "ready" else "ACTIVE"
        self.deadline = time.monotonic() + self._armed_timeout_s
        try:
            for trial in trials:
                tune_controller._schedule_trial_train(trial)
                self.release_attempts[released_phase].append(trial.trial_id)
        except Exception:
            self.phase = "FAILED"
            tune_controller.request_stop_experiment()
            raise


def train_member(config):
    member = config["clan_member"]
    tune.report({"user_started": True, "member_id": member["member_id"], "user_pid": os.getpid()})


def main():
    scheduler = ClanPopulationAdmissionScheduler()
    search = BasicVariantGenerator(max_concurrent=0)
    ray.init(num_cpus=2, include_dashboard=False)
    try:
        results = tune.Tuner(
            tune.with_resources(ClanMemberAdmission(train_member), {"cpu": 1}),
            param_space={
                "clan_member": tune.grid_search([
                    {"member_id": 0, "rank": 0, "world_size": 2},
                    {"member_id": 1, "rank": 1, "world_size": 2},
                ])
            },
            tune_config=tune.TuneConfig(
                search_alg=search,
                scheduler=scheduler,
                reuse_actors=False,
            ),
            run_config=tune.RunConfig(verbose=0),
        ).fit()
    finally:
        ray.shutdown()

    assert scheduler.phase == "ACTIVE"
    assert not scheduler.errors
    assert len(scheduler.ready) == len(scheduler.armed) == 2
    assert len(scheduler.release_attempts["ready"]) == 2
    assert len(scheduler.release_attempts["armed"]) == 2
    ready_pids = {record["pid"] for record in scheduler.ready.values()}
    armed_pids = {record["pid"] for record in scheduler.armed.values()}
    assert ready_pids == armed_pids
    assert len(ready_pids) == 2
    assert not [result.error for result in results if result.error]
    final = sorted((result.metrics["member_id"], result.metrics["user_started"], result.metrics["user_pid"]) for result in results)
    evidence = {
        "ray_version": ray.__version__,
        "phase": scheduler.phase,
        "ready": scheduler.ready,
        "armed": scheduler.armed,
        "release_attempts": scheduler.release_attempts,
        "final": final,
    }
    print("ADMISSION_PROBE_PASS", evidence)


if __name__ == "__main__":
    main()
