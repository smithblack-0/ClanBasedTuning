"""Native Ray Tune/PBT integration contract for one complete clan exploit cycle."""

from __future__ import annotations

# Ray is optional, so the module-level skip necessarily precedes Ray-dependent imports.
# ruff: noqa: E402
import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
ray = pytest.importorskip("ray")

import torch
from lightning import LightningModule, Trainer
from ray import tune
from torch import Tensor, nn
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import (
    ClanBasedTraining,
    make_clan_lightning_plugins,
    prepare_clan_trainer,
    replicated_sampler,
    tune_checkpoint_path,
)


class _RayScalarTrial(LightningModule):
    def __init__(self) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.tensor([1.0]))

    def training_step(self, batch: tuple[Tensor], batch_idx: int) -> Tensor:
        del batch, batch_idx
        return self.weight.square().sum()

    def validation_step(self, batch: tuple[Tensor], batch_idx: int) -> None:
        del batch, batch_idx
        optimizer = self.trainer.optimizers[0]
        # The rank term deterministically makes rank 0 the first source trial.
        fitness = self.weight.square().mean() + 0.01 * self.global_rank
        self.log("fitness", fitness, sync_dist=False, on_step=False, on_epoch=True)
        self.log(
            "learning_rate",
            float(optimizer.param_groups[0]["lr"]),
            sync_dist=False,
            on_step=False,
            on_epoch=True,
        )

    def configure_optimizers(self) -> torch.optim.Optimizer:
        # Deliberately wrong. ClanDDPStrategy must apply the Tune trial config.
        return torch.optim.SGD([self.weight], lr=9.0, momentum=0.9)


def test_native_tune_trials_exploit_restore_and_reform_clan(tmp_path):
    scheduler = ClanBasedTraining(
        population_size=2,
        rendezvous_timeout_s=60.0,
        metric="fitness",
        mode="min",
        perturbation_interval=1,
        quantile_fraction=0.5,
        hyperparam_mutations={"lr": lambda: 0.1},
        resample_probability=0.0,
        perturbation_factors=(2.0, 2.0),
        log_config=False,
    )

    def train(config):
        model = _RayScalarTrial()
        clan = make_clan_lightning_plugins(
            config,
            metrics={"fitness": "fitness", "learning_rate": "learning_rate"},
            process_group_backend="gloo",
        )
        trainer = Trainer(
            accelerator="cpu",
            devices=1,
            num_nodes=1,
            strategy=clan.strategy,
            plugins=[clan.environment],
            max_epochs=10,
            logger=False,
            callbacks=[clan.report_callback],
            enable_checkpointing=False,
            enable_progress_bar=False,
            enable_model_summary=False,
            num_sanity_val_steps=0,
        )
        train_loader = DataLoader(TensorDataset(torch.zeros(2)), batch_size=1)
        validation_dataset = TensorDataset(torch.zeros(2))
        validation_loader = DataLoader(
            validation_dataset,
            batch_size=1,
            sampler=replicated_sampler(validation_dataset),
        )
        prepare_clan_trainer(trainer)
        with tune_checkpoint_path() as checkpoint_path:
            trainer.fit(
                model,
                train_dataloaders=train_loader,
                val_dataloaders=validation_loader,
                ckpt_path=checkpoint_path,
            )

    ray.init(num_cpus=2, include_dashboard=False, ignore_reinit_error=True)
    try:
        tuner = tune.Tuner(
            tune.with_resources(train, {"cpu": 1}),
            param_space={},
            run_config=tune.RunConfig(
                storage_path=str(tmp_path),
                stop={"training_iteration": 2},
                failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
                verbose=0,
            ),
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                num_samples=2,
                max_concurrent_trials=2,
                reuse_actors=False,
            ),
        )
        results = tuner.fit()
    finally:
        ray.shutdown()

    errors = [result.error for result in results if result.error is not None]
    assert not errors
    learning_rates = sorted(float(result.metrics["learning_rate"]) for result in results)
    assert learning_rates == pytest.approx([0.1, 0.2])
