"""Framework contracts for bounded Clan failure behavior.

The normal suite proves that insufficient resources fail through the existing rendezvous
boundary instead of hanging indefinitely. A separate destructive participant-exit test is
available for explicit local qualification because intentionally killing a live DDP rank is
not appropriate for every CI run.
"""

import contextlib
import os
import time
from pathlib import Path

import pytest
import ray
from ray import tune
from ray.tune.error import TuneError

from tests.support.tiny_mlp import (
    build_tiny_scheduler,
    tiny_param_space,
    tiny_tune_config,
    train_tiny_mlp_member,
)

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def _error_texts(storage_path: Path) -> list[str]:
    return [path.read_text(errors="replace") for path in storage_path.rglob("error.txt")]


@pytest.mark.failure_contract
def test_insufficient_capacity_fails_with_bounded_rendezvous(tmp_path: Path) -> None:
    """One available CPU cannot silently run half of a two-member Clan forever."""

    ray.shutdown()
    ray.init(num_cpus=1, include_dashboard=False, log_to_driver=False)
    started = time.monotonic()
    try:
        tuner = tune.Tuner(
            tune.with_resources(train_tiny_mlp_member, {"cpu": 1}),
            param_space=tiny_param_space(accelerator="cpu", ddp_timeout_s=5.0),
            tune_config=tiny_tune_config(build_tiny_scheduler(join_timeout_s=1.0)),
            run_config=tune.RunConfig(
                name="insufficient-capacity-contract",
                storage_path=str(tmp_path),
                stop={"training_iteration": 1},
                verbose=0,
            ),
        )
        with contextlib.suppress(TuneError):
            tuner.fit()
    finally:
        elapsed = time.monotonic() - started
        ray.shutdown()

    assert elapsed < 20.0
    errors = _error_texts(tmp_path)
    assert errors
    assert any("complete Clan did not become resident" in text for text in errors)


@pytest.mark.failure_contract
@pytest.mark.requires_failure_injection
def test_active_collective_peer_exit_is_bounded(tmp_path: Path) -> None:
    """Opt-in test kills one live DDP member and requires the experiment to terminate."""

    if os.environ["CLAN_RUN_DESTRUCTIVE_FAILURE"] != "1" if "CLAN_RUN_DESTRUCTIVE_FAILURE" in os.environ else True:
        pytest.skip("set CLAN_RUN_DESTRUCTIVE_FAILURE=1 to run destructive peer-exit qualification")

    param_space = tiny_param_space(accelerator="cpu", ddp_timeout_s=5.0)
    param_space["crash_member_id"] = 0
    param_space["crash_after_global_step"] = 0

    ray.shutdown()
    ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
    started = time.monotonic()
    try:
        tuner = tune.Tuner(
            tune.with_resources(train_tiny_mlp_member, {"cpu": 1}),
            param_space=param_space,
            tune_config=tiny_tune_config(build_tiny_scheduler(join_timeout_s=10.0)),
            run_config=tune.RunConfig(
                name="active-peer-exit-contract",
                storage_path=str(tmp_path),
                stop={"training_iteration": 1},
                verbose=0,
            ),
        )
        with contextlib.suppress(TuneError):
            tuner.fit()
    finally:
        elapsed = time.monotonic() - started
        ray.shutdown()

    assert elapsed < 30.0
    assert _error_texts(tmp_path)
