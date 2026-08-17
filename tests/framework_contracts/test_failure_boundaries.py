"""Framework contracts that distinguish CBT-owned admission failure from backend failure.

Insufficient resident capacity is a CBT problem because CBT requires the whole Clan before DDP
can exist; both trials must therefore fail at the Clan rendezvous boundary, not later in
PyTorch networking. Loss of a participant after DDP is active belongs to the distributed
backend, so that destructive qualification is opt-in and checks only bounded experiment
termination rather than inventing a CBT recovery mechanism.
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
    """Use Tune's persisted per-trial errors as evidence of which failure boundary actually won.

    Inspecting stored errors after Ray shuts down avoids relying on console formatting or which
    trial happened to fail first. The contract needs every member's terminal cause because a
    stale rendezvous can make the first member fail correctly while a later member reaches DDP.
    """

    return [path.read_text(errors="replace") for path in storage_path.rglob("error.txt")]


@pytest.mark.failure_contract
def test_insufficient_capacity_fails_at_clan_rendezvous_boundary(tmp_path: Path) -> None:
    """A partial Clan must never be time-multiplexed into a later dead-peer DDP attempt."""

    ray.shutdown()
    ray.init(num_cpus=1, include_dashboard=False, log_to_driver=False)
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
        ray.shutdown()

    errors = _error_texts(tmp_path)
    assert len(errors) == 2
    assert all("complete Clan did not become resident" in text for text in errors)
    assert all("DistNetworkError" not in text for text in errors)


@pytest.mark.failure_contract
@pytest.mark.requires_failure_injection
def test_active_collective_peer_exit_is_bounded(tmp_path: Path) -> None:
    """A hard rank exit must surface through framework failure rather than hang indefinitely.

    ``TinyRegressionModel`` uses ``os._exit`` so Lightning cannot perform graceful teardown.
    The test deliberately does not require CBT recovery or a particular backend exception; once
    the process group exists, PyTorch/Ray own failure propagation. The bounded wall clock is a
    qualification guard against an indefinitely stuck experiment, not a normal-runtime SLO.
    """

    if (
        "CLAN_RUN_DESTRUCTIVE_FAILURE" not in os.environ
        or os.environ["CLAN_RUN_DESTRUCTIVE_FAILURE"] != "1"
    ):
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
