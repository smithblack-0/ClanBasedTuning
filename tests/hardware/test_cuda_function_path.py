"""Local two-GPU CUDA/NCCL qualification for the public Clan function path.

The test uses the tiny MLP/AdamW workload and two Tune trials requesting one GPU each. It
self-skips when fewer than two local CUDA devices are visible, so developers can keep the
same repository test command on CPU-only machines without weakening the hardware contract.
"""

from pathlib import Path

import pytest
import ray
import torch
from ray import tune

from tests.support.tiny_mlp import (
    build_tiny_scheduler,
    tiny_param_space,
    tiny_tune_config,
    train_tiny_mlp_member,
)

pytestmark = [
    pytest.mark.framework_contract,
    pytest.mark.requires_ray,
    pytest.mark.requires_gpu,
]


def test_two_cuda_members_train_through_nccl(tmp_path: Path) -> None:
    """Two one-GPU Tune members form one NCCL world and repeat a Clan transition."""

    if not torch.cuda.is_available() or torch.cuda.device_count() < 2:
        pytest.skip("two visible CUDA devices are required for the local Clan GPU contract")

    ray.shutdown()
    ray.init(num_cpus=2, num_gpus=2, include_dashboard=False, log_to_driver=False)
    try:
        results = tune.Tuner(
            tune.with_resources(train_tiny_mlp_member, {"cpu": 1, "gpu": 1}),
            param_space=tiny_param_space(accelerator="gpu"),
            tune_config=tiny_tune_config(build_tiny_scheduler()),
            run_config=tune.RunConfig(
                name="tiny-mlp-cuda-contract",
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
        assert result.metrics["restored_global_step"] > 0
        assert result.metrics["lr_seen"] == pytest.approx(result.config["lr"])
        assert result.metrics["device_is_cuda"] == pytest.approx(1.0)
        assert result.metrics["backend_is_nccl"] == pytest.approx(1.0)
        assert result.metrics["world_size_seen"] == pytest.approx(2.0)
