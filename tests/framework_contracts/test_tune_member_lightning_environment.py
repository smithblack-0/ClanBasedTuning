"""Framework contracts for one externally launched Tune process per Lightning DDP rank.

The focused environment contract establishes the logical one-process-node topology supplied
to Lightning. The distributed contract then runs two real Tune trials in one PyTorch DDP
world and proves that Lightning performs ordinary gradient all-reduce without CBT owning a
second collective implementation.
"""

import socket
from datetime import timedelta
from pathlib import Path
from typing import Any

import lightning.pytorch as lightning
import pytest
import ray
import torch
from lightning.pytorch.strategies import DDPStrategy
from ray import tune
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning.lightning_environment import TuneMemberEnvironment

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def _free_local_port() -> int:
    """Choose a best-effort local rendezvous port for this short-lived framework contract."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _run_ddp_member(config: dict[str, Any]) -> None:
    """Prove an independently launched Tune process can remain ordinary Lightning DDP.

    Each trial constructs only topology metadata; ``DDPStrategy`` still creates the real
    process group and performs gradient reduction. The rank-specific local gradients make an
    accidental non-DDP or wrong-world execution observable in the final parameter value.
    """

    torch.set_num_threads(1)

    class OneStepModel(lightning.LightningModule):
        """Expose framework-created topology and the post-DDP reduced gradient."""

        def __init__(self, local_gradient: float) -> None:
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(0.0))
            self.local_gradient = local_gradient
            self.observed_rank: int | None = None
            self.observed_world_size: int | None = None
            self.observed_backend: str | None = None
            self.reduced_gradient: float | None = None

        def training_step(self, batch: list[torch.Tensor], batch_index: int) -> torch.Tensor:
            """Create different local gradients so a shared DDP reduction is test-visible."""

            del batch, batch_index
            return self.weight * self.local_gradient

        def configure_optimizers(self) -> torch.optim.Optimizer:
            """Use unit SGD so the reduced gradient is directly visible in the update."""

            return torch.optim.SGD(self.parameters(), lr=1.0)

        def on_train_start(self) -> None:
            """Capture the topology after Lightning, not CBT, has initialized the process group."""

            self.observed_rank = torch.distributed.get_rank()
            self.observed_world_size = torch.distributed.get_world_size()
            self.observed_backend = torch.distributed.get_backend()

        def on_before_optimizer_step(self, optimizer: torch.optim.Optimizer) -> None:
            """Observe the gradient only after Lightning DDP has performed its reduction."""

            del optimizer
            self.reduced_gradient = float(self.weight.grad.detach().item())

    environment = TuneMemberEnvironment(
        global_rank=int(config["member_id"]),
        world_size=int(config["world_size"]),
        main_address=str(config["main_address"]),
        main_port=int(config["main_port"]),
    )
    strategy = DDPStrategy(
        cluster_environment=environment,
        process_group_backend="gloo",
        timeout=timedelta(seconds=60),
    )
    model = OneStepModel(local_gradient=float(config["member_id"] + 1))
    training_data = DataLoader(TensorDataset(torch.tensor([0.0])), batch_size=1)
    trainer = lightning.Trainer(
        accelerator="cpu",
        devices=1,
        num_nodes=int(config["world_size"]),
        strategy=strategy,
        max_steps=1,
        logger=False,
        enable_checkpointing=False,
        enable_model_summary=False,
        enable_progress_bar=False,
    )

    trainer.fit(model, train_dataloaders=training_data)

    tune.report(
        {
            "member_id": config["member_id"],
            "global_rank": model.observed_rank,
            "world_size": model.observed_world_size,
            "backend": model.observed_backend,
            "reduced_gradient": model.reduced_gradient,
            "final_weight": float(model.weight.detach().item()),
            "group_active_until_trial_exit": torch.distributed.is_initialized(),
        }
    )


def test_environment_exposes_logical_one_process_nodes() -> None:
    """The adapter derives local/node ranks from one external stable member identity."""

    environment = TuneMemberEnvironment(
        global_rank=1,
        world_size=3,
        main_address="127.0.0.1",
        main_port=12_345,
    )

    assert environment.creates_processes_externally is True
    assert environment.detect() is False
    assert environment.global_rank() == 1
    assert environment.world_size() == 3
    assert environment.local_rank() == 0
    assert environment.node_rank() == 1
    assert environment.main_address == "127.0.0.1"
    assert environment.main_port == 12_345

    environment.set_global_rank(1)
    environment.set_world_size(3)

    with pytest.raises(RuntimeError, match="global rank conflicts"):
        environment.set_global_rank(0)
    with pytest.raises(RuntimeError, match="world size conflicts"):
        environment.set_world_size(2)


def test_two_tune_trials_form_one_framework_managed_ddp_world(tmp_path: Path) -> None:
    """Two Tune processes become ranks of one native Lightning/PyTorch DDP world."""

    ray.shutdown()
    ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
    try:
        world_size = 2
        tuner = tune.Tuner(
            tune.with_resources(_run_ddp_member, {"cpu": 1}),
            param_space={
                "member_id": tune.grid_search([0, 1]),
                "world_size": world_size,
                "main_address": "127.0.0.1",
                "main_port": _free_local_port(),
            },
            tune_config=tune.TuneConfig(max_concurrent_trials=world_size),
            run_config=tune.RunConfig(
                name="tune-member-ddp-contract",
                storage_path=str(tmp_path),
                verbose=0,
            ),
        )

        results = tuner.fit()
    finally:
        ray.shutdown()

    assert len(results) == world_size
    assert all(result.error is None for result in results)

    metrics = sorted((result.metrics for result in results), key=lambda item: item["member_id"])
    assert [item["member_id"] for item in metrics] == [0, 1]
    assert [item["global_rank"] for item in metrics] == [0, 1]
    assert [item["world_size"] for item in metrics] == [2, 2]
    assert [item["backend"] for item in metrics] == ["gloo", "gloo"]
    assert [item["reduced_gradient"] for item in metrics] == pytest.approx([1.5, 1.5])
    assert [item["final_weight"] for item in metrics] == pytest.approx([-1.5, -1.5])
    assert [item["group_active_until_trial_exit"] for item in metrics] == [True, True]
