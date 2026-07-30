"""Ray contract for collective fan-out after one unrecoverable member failure."""

from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
ray = pytest.importorskip("ray")

from ray import tune  # noqa: E402
from ray.tune.schedulers import FIFOScheduler  # noqa: E402

from clan_based_tuning.ray_schedulers import (  # noqa: E402
    ClanCollectiveFailureScheduler,
)


def _fail_one_member(config):
    tune.report({"member_id": config["member_id"], "ready": True})
    if config["member_id"] == 0:
        time.sleep(1.0)
        raise RuntimeError("intentional Clan member failure")

    for iteration in range(600):
        time.sleep(0.1)
        tune.report({"member_id": config["member_id"], "iteration": iteration})


def test_one_member_error_stops_survivors_and_remains_visible(tmp_path):
    scheduler = ClanCollectiveFailureScheduler(downstream=FIFOScheduler())
    ray.init(num_cpus=2, include_dashboard=False, ignore_reinit_error=True)
    try:
        result_grid = tune.Tuner(
            tune.with_resources(_fail_one_member, {"cpu": 1}),
            param_space={"member_id": tune.grid_search([0, 1])},
            run_config=tune.RunConfig(
                storage_path=str(tmp_path),
                failure_config=tune.FailureConfig(max_failures=0),
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

    errors = [result.error for result in result_grid if result.error is not None]
    assert len(errors) == 1
    assert "intentional Clan member failure" in str(errors[0])
    assert len(result_grid) == 2
