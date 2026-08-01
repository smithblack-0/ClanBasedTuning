"""Framework contract for one Tune trial per Lightning/PyTorch DDP rank."""

from __future__ import annotations

import socket
from datetime import timedelta

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _run_ddp_member(config):
    import lightning.pytorch as lightning
    import torch
    from lightning.pytorch.strategies import DDPStrategy
    from ray import tune
    from torch.utils.data import DataLoader, TensorDataset

    from clan_based_tuning.lightning_environment import TuneMemberEnvironment

    torch.set_num_threads(1)

    class OneStepModel(lightning.LightningModule):
        def __init__(self, local_gradient: float):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(0.0))
            self.local_gradient = local_gradient
            self.observed_rank = None
            self.observed_world_size = None
            self.observed_backend = None
            self.reduced_gradient = None

        def training_step(self, batch, batch_index):
            del batch, batch_index
            return self.weight * self.local_gradient

        def configure_optimizers(self):
            return torch.optim.SGD(self.parameters(), lr=1.0)

        def on_train_start(self):
            self.observed_rank = torch.distributed.get_rank()
            self.observed_world_size = torch.distributed.get_world_size()
            self.observed_backend = torch.distributed.get_backend()

        def on_before_optimizer_step(self, optimizer):
            del optimizer
            self.reduced_gradient = float(self.weight.grad.detach().item())

    environment = TuneMemberEnvironment(
        global_rank=config["member_id"],
        world_size=config["world_size"],
        local_rank=0,
        node_rank=config["member_id"],
        main_address=config["main_address"],
        main_port=config["main_port"],
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
        num_nodes=config["world_size"],
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


def test_environment_reports_external_topology_without_mutating_it():
    from clan_based_tuning.lightning_environment import TuneMemberEnvironment

    environment = TuneMemberEnvironment(
        global_rank=1,
        world_size=3,
        local_rank=0,
        node_rank=1,
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


def test_two_tune_trials_form_one_framework_managed_ddp_world(tmp_path):
    import ray
    from ray import tune

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
