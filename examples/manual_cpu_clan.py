"""Run the explicit Milestone 3 Clan composition on two CPU Tune trials.

Install the development and Ray dependencies, then run:

    python examples/manual_cpu_clan.py --storage-path /tmp/clan-manual

The example intentionally exposes every integration component. It uses a one-parameter
model so the shared gradient, optimizer-driven divergence, sole parent, checkpoint
inheritance, and replay path remain directly inspectable.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import ray
import torch
from lightning import LightningModule, Trainer
from ray import tune
from torch import Tensor, nn
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import (
    ClanBasedTraining,
    ClanController,
    ClanControllerRestore,
    ClanDDPStrategy,
    ClanLightningEnvironment,
    ClanTuneReportCallback,
    ClanTuneSession,
    MutationSpec,
    replicated_sampler,
    tune_checkpoint_path,
)


class ScalarModel(LightningModule):
    """One scalar whose exact state transition can be read from Tune results."""

    def __init__(self) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.tensor([1.0]))
        self.window_start_weight = torch.tensor(float("nan"))
        self.reduced_gradient = torch.tensor(float("nan"))

    def on_train_start(self) -> None:
        self.window_start_weight = self.weight.detach().clone()

    def training_step(self, batch: tuple[Tensor], batch_idx: int) -> Tensor:
        del batch_idx
        (target,) = batch
        return (self.weight - target).square().mean()

    def on_after_backward(self) -> None:
        if self.weight.grad is None:
            raise RuntimeError("Expected DDP to produce a reduced gradient")
        self.reduced_gradient = self.weight.grad.detach().clone()

    def validation_step(self, batch: tuple[Tensor], batch_idx: int) -> None:
        del batch, batch_idx
        optimizer = self.trainer.optimizers[0]
        values = {
            "fitness": (self.weight - 1.5).square().mean(),
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "weight": self.weight.detach().mean(),
            "reduced_gradient": self.reduced_gradient.mean(),
            "window_start_weight": self.window_start_weight.mean(),
        }
        for name, value in values.items():
            self.log(name, value, sync_dist=False, on_step=False, on_epoch=True)

    def configure_optimizers(self) -> torch.optim.Optimizer:
        # The restore callback replaces this deliberately wrong learning rate.
        return torch.optim.SGD([self.weight], lr=9.0, momentum=0.9)


def train_member(config) -> None:
    session = ClanTuneSession(config)
    controller = ClanController(
        member_id=session.member_id,
        population_size=session.population_size,
        initial_config={"lr": 0.05 * (session.member_id + 1)},
        mutations={
            "lr": MutationSpec(
                standard_deviation=0.02,
                geometry="linear",
                minimum=0.01,
                maximum=0.2,
            )
        },
        mode="min",
        seed=int(config["trial_seed"]),
        save_member_fitness=session.save_member_fitness,
        load_population=session.load_population,
    )
    restore = ClanControllerRestore(controller)
    report = ClanTuneReportCallback(
        controller,
        metrics={
            "fitness": "fitness",
            "learning_rate": "learning_rate",
            "weight": "weight",
            "reduced_gradient": "reduced_gradient",
            "window_start_weight": "window_start_weight",
        },
        fitness_metric="fitness",
    )
    trainer = Trainer(
        accelerator="cpu",
        devices=1,
        num_nodes=1,
        strategy=ClanDDPStrategy(session.runtime, process_group_backend="gloo"),
        plugins=[ClanLightningEnvironment(session.runtime)],
        callbacks=[restore, report],
        max_epochs=10,
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
    )
    train_loader = DataLoader(
        TensorDataset(torch.tensor([0.0, 1.0, 2.0, 3.0])),
        batch_size=1,
    )
    validation_data = TensorDataset(torch.tensor([1.5, 1.5]))
    validation_loader = DataLoader(
        validation_data,
        batch_size=1,
        sampler=replicated_sampler(validation_data),
    )
    with tune_checkpoint_path() as checkpoint_path:
        trainer.fit(
            ScalarModel(),
            train_dataloaders=train_loader,
            val_dataloaders=validation_loader,
            ckpt_path=checkpoint_path,
        )


def main(storage_path: Path) -> None:
    population_size = 2
    scheduler = ClanBasedTraining(
        population_size=population_size,
        metric="fitness",
        mode="min",
        perturbation_interval=1,
    )
    ray.init(num_cpus=population_size, include_dashboard=False)
    try:
        results = tune.Tuner(
            tune.with_resources(train_member, {"cpu": 1}),
            param_space={"trial_seed": tune.grid_search([17, 23])},
            run_config=tune.RunConfig(
                storage_path=str(storage_path),
                stop={"training_iteration": 3},
                checkpoint_config=tune.CheckpointConfig(num_to_keep=4),
                failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
            ),
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                max_concurrent_trials=population_size,
                reuse_actors=False,
            ),
        ).fit()
    finally:
        ray.shutdown()

    if any(result.error is not None for result in results):
        raise RuntimeError("At least one Clan member failed; inspect the Tune result directory")

    print("\nFinal member results")
    for result in results:
        metrics = result.metrics
        print(
            {
                "trial": result.path,
                "fitness": metrics["fitness"],
                "learning_rate": metrics["learning_rate"],
                "weight": metrics["weight"],
                "reduced_gradient": metrics["reduced_gradient"],
                "window_start_weight": metrics["window_start_weight"],
            }
        )
    print("\nSelected parent path")
    for decision in scheduler.selection_path:
        print(decision)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--storage-path",
        type=Path,
        default=Path("/tmp/clan-based-tuning-manual"),
    )
    main(parser.parse_args().storage_path)
