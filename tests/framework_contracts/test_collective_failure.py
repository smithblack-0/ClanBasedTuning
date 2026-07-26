from __future__ import annotations

# Ray is optional, so the module-level skip necessarily precedes Ray-dependent imports.
# ruff: noqa: E402
import time

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
ray = pytest.importorskip("ray")

from ray import tune

from clan_based_tuning import ClanBasedTraining, ClanTuneSession


def test_one_member_failure_invalidates_the_complete_clan(tmp_path):
    scheduler = ClanBasedTraining(
        population_size=2,
        rendezvous_timeout_s=1.0,
        rendezvous_poll_interval_s=0.05,
        metric="fitness",
        mode="min",
        perturbation_interval=1,
    )

    def train(config):
        session = ClanTuneSession(config)
        if session.member_id == 0:
            raise RuntimeError("deliberate Clan member failure")
        session.load_population(0)

    started = time.perf_counter()
    ray.init(num_cpus=2, include_dashboard=False, ignore_reinit_error=True)
    try:
        results = tune.Tuner(
            tune.with_resources(train, {"cpu": 1}),
            param_space={"trial_seed": tune.grid_search([17, 23])},
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
        ).fit()
    finally:
        ray.shutdown()

    assert any(result.error is not None for result in results)
    assert time.perf_counter() - started < 15.0
