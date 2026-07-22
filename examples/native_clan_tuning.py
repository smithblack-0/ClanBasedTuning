"""Run a minimal two-member Clan Based Training experiment on CPU."""

from __future__ import annotations

import ray
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

POPULATION_SIZE = 2


class ScalarModel(LightningModule):
    """Small model whose members visibly diverge under different learning rates."""

    def __init__(self, config: dict[str, float]) -> None:
        super().__init__()
        self.config = config
        self.weight = nn.Parameter(torch.tensor([1.0]))

    def training_step(self, batch: tuple[Tensor], batch_idx: int) -> Tensor:
        del batch, batch_idx
        return self.weight.square().sum()

    def validation_step(self, batch: tuple[Tensor], batch_idx: int) -> None:
        del batch, batch_idx
        self.log(
            "fitness",
            self.weight.square().mean(),
            on_step=False,
            on_epoch=True,
            sync_dist=False,
        )

    def configure_optimizers(self) -> torch.optim.Optimizer:
        return torch.optim.SGD(
            [self.weight],
            lr=self.config["lr"],
            momentum=0.9,
        )


def train(config: dict[str, float]) -> None:
    clan = make_clan_lightning_plugins(
        config,
        metrics={"fitness": "fitness"},
        process_group_backend="gloo",
    )
    trainer = Trainer(
        accelerator="cpu",
        devices=1,
        num_nodes=1,
        strategy=clan.strategy,
        plugins=[clan.environment],
        callbacks=[clan.report_callback],
        enable_checkpointing=False,
        logger=False,
        max_epochs=20,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
    )
    prepare_clan_trainer(trainer)

    training_data = TensorDataset(torch.zeros(8))
    validation_data = TensorDataset(torch.zeros(8))
    training_loader = DataLoader(training_data, batch_size=2)
    validation_loader = DataLoader(
        validation_data,
        batch_size=2,
        sampler=replicated_sampler(validation_data),
    )

    with tune_checkpoint_path() as checkpoint_path:
        trainer.fit(
            ScalarModel(config),
            train_dataloaders=training_loader,
            val_dataloaders=validation_loader,
            ckpt_path=checkpoint_path,
        )


def main() -> None:
    scheduler = ClanBasedTraining(
        population_size=POPULATION_SIZE,
        metric="fitness",
        mode="min",
        time_attr="training_iteration",
        perturbation_interval=1,
        hyperparam_mutations={"lr": tune.loguniform(1e-3, 3e-1)},
    )

    ray.init(num_cpus=POPULATION_SIZE, include_dashboard=False)
    try:
        results = tune.Tuner(
            tune.with_resources(train, {"cpu": 1}),
            param_space={"lr": tune.loguniform(1e-3, 3e-1)},
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                num_samples=POPULATION_SIZE,
                max_concurrent_trials=POPULATION_SIZE,
                reuse_actors=False,
            ),
            run_config=tune.RunConfig(
                stop={"training_iteration": 3},
                failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
            ),
        ).fit()
    finally:
        ray.shutdown()

    if errors := [result.error for result in results if result.error is not None]:
        raise RuntimeError(errors)
    print(results.get_best_result(metric="fitness", mode="min").metrics)


if __name__ == "__main__":
    main()
