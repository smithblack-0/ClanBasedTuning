"""Small realistic CPU end-to-end contract for the public Clan function path.

The scalar mechanics contract proves exact state-transfer details. This test adds a normal
forward/loss/backward path with a two-layer MLP and AdamW so production-readiness work is not
based only on a one-parameter synthetic model.
"""

import math
from pathlib import Path

import pytest
import ray
from ray import tune

from tests.support.tiny_mlp import (
    build_tiny_scheduler,
    tiny_param_space,
    tiny_tune_config,
    train_tiny_mlp_member,
)

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def test_tiny_mlp_repeats_training_and_optimizer_restoration(tmp_path: Path) -> None:
    """Two CPU members train, select, restore AdamW state, and apply child genomes."""

    ray.shutdown()
    ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
    try:
        results = tune.Tuner(
            tune.with_resources(train_tiny_mlp_member, {"cpu": 1}),
            param_space=tiny_param_space(accelerator="cpu"),
            tune_config=tiny_tune_config(build_tiny_scheduler()),
            run_config=tune.RunConfig(
                name="tiny-mlp-cpu-contract",
                storage_path=str(tmp_path),
                stop={"training_iteration": 2},
                verbose=0,
            ),
        ).fit()
    finally:
        ray.shutdown()

    assert len(results) == 2
    assert all(result.error is None for result in results)
    for result in results:
        assert result.metrics["training_iteration"] >= 2
        assert math.isfinite(float(result.metrics["val_loss"]))
        assert result.metrics["lr_seen"] == pytest.approx(result.config["lr"])
        assert result.metrics["weight_decay_seen"] == pytest.approx(result.config["weight_decay"])
        assert result.metrics["restored_global_step"] > 0
        assert result.metrics["device_is_cuda"] == pytest.approx(0.0)
        assert result.metrics["backend_is_nccl"] == pytest.approx(0.0)
        assert result.metrics["world_size_seen"] == pytest.approx(2.0)
