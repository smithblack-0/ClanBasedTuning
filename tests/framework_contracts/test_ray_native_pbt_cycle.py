"""Real CPU Ray/Lightning/DDP contract for repeated winner-only Clan rounds."""

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


class _RayScalarTrial(LightningModule):
    def __init__(self) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.tensor([1.0]))
        self.last_reduced_gradient = torch.tensor(float("nan"))
        self.window_start_weight = torch.tensor(float("nan"))

    def on_train_start(self) -> None:
        self.window_start_weight = self.weight.detach().clone()

    def training_step(self, batch: tuple[Tensor], batch_idx: int) -> Tensor:
        del batch_idx
        (target,) = batch
        return (self.weight - target).square().mean()

    def on_after_backward(self) -> None:
        assert self.weight.grad is not None
        self.last_reduced_gradient = self.weight.grad.detach().clone()

    def validation_step(self, batch: tuple[Tensor], batch_idx: int) -> None:
        del batch, batch_idx
        optimizer = self.trainer.optimizers[0]
        fitness = (self.weight - 1.5).square().mean()
        values = {
            "fitness": fitness,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "weight": self.weight.detach().mean(),
            "reduced_gradient": self.last_reduced_gradient.mean(),
            "window_start_weight": self.window_start_weight.mean(),
        }
        for name, value in values.items():
            self.log(name, value, sync_dist=False, on_step=False, on_epoch=True)

    def configure_optimizers(self) -> torch.optim.Optimizer:
        # Deliberately wrong. ClanControllerRestore applies the local controller config.
        return torch.optim.SGD([self.weight], lr=9.0, momentum=0.9)


def test_manual_cpu_clan_runs_repeated_winner_only_transitions(tmp_path):
    population_size = 2
    scheduler = ClanBasedTraining(
        population_size=population_size,
        rendezvous_timeout_s=60.0,
        metric="fitness",
        mode="min",
        perturbation_interval=1,
    )

    def train(config):
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
        strategy = ClanDDPStrategy(session.runtime, process_group_backend="gloo")
        environment = ClanLightningEnvironment(session.runtime)
        trainer = Trainer(
            accelerator="cpu",
            devices=1,
            num_nodes=1,
            strategy=strategy,
            plugins=[environment],
            max_epochs=10,
            logger=False,
            callbacks=[restore, report],
            enable_checkpointing=False,
            enable_progress_bar=False,
            enable_model_summary=False,
            num_sanity_val_steps=0,
        )
        model = _RayScalarTrial()
        train_loader = DataLoader(
            TensorDataset(torch.tensor([0.0, 1.0, 2.0, 3.0])),
            batch_size=1,
        )
        validation_dataset = TensorDataset(torch.tensor([1.5, 1.5]))
        validation_loader = DataLoader(
            validation_dataset,
            batch_size=1,
            sampler=replicated_sampler(validation_dataset),
        )
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
            param_space={"trial_seed": tune.grid_search([17, 23])},
            run_config=tune.RunConfig(
                storage_path=str(tmp_path),
                stop={"training_iteration": 2},
                checkpoint_config=tune.CheckpointConfig(num_to_keep=4),
                failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
                verbose=0,
            ),
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                max_concurrent_trials=population_size,
                reuse_actors=False,
            ),
        )
        results = tuner.fit()
    finally:
        ray.shutdown()

    errors = [result.error for result in results if result.error is not None]
    assert not errors
    metrics = [result.metrics for result in results]
    assert len(metrics) == population_size

    reduced_gradients = [float(item["reduced_gradient"]) for item in metrics]
    assert reduced_gradients[0] == pytest.approx(reduced_gradients[1])

    start_weights = [float(item["window_start_weight"]) for item in metrics]
    assert start_weights[0] == pytest.approx(start_weights[1])

    learning_rates = [float(item["learning_rate"]) for item in metrics]
    weights = [float(item["weight"]) for item in metrics]
    assert learning_rates[0] != pytest.approx(learning_rates[1])
    assert weights[0] != pytest.approx(weights[1])

    assert scheduler._num_checkpoints == 2
    assert scheduler._num_perturbations == 2
    assert [item["round_index"] for item in scheduler.selection_path] == [0, 1]
