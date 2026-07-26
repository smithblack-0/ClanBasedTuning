"""Initial scientific workload for the explicit Milestone 3 Clan path.

The experiment trains a small neural classifier on Fisher's Iris dataset from
``sklearn.datasets``. It is deliberately modest: the goal is to establish that the
public integrated product can investigate optimizer-policy adaptation, not to claim
that Clan Tuning improves this easy classification task.

Run:

    python examples/iris_clan_experiment.py --storage-path /tmp/clan-iris
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import ray
import torch
import torch.nn.functional as functional
from lightning import LightningModule, Trainer
from ray import tune
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
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

POPULATION_SIZE = 2
REPORTS_PER_TRIAL = 5
TRAIN_SAMPLES = 120
VALIDATION_SAMPLES = 30


class IrisClassifier(LightningModule):
    def __init__(self) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(4, 16),
            nn.Tanh(),
            nn.Linear(16, 3),
        )

    def training_step(self, batch: tuple[Tensor, Tensor], batch_idx: int) -> Tensor:
        del batch_idx
        features, labels = batch
        return functional.cross_entropy(self.network(features), labels)

    def validation_step(self, batch: tuple[Tensor, Tensor], batch_idx: int) -> None:
        del batch_idx
        features, labels = batch
        logits = self.network(features)
        loss = functional.cross_entropy(logits, labels)
        accuracy = (logits.argmax(dim=1) == labels).float().mean()
        self.log(
            "validation_loss",
            loss,
            sync_dist=False,
            on_step=False,
            on_epoch=True,
            batch_size=len(labels),
        )
        self.log(
            "validation_accuracy",
            accuracy,
            sync_dist=False,
            on_step=False,
            on_epoch=True,
            batch_size=len(labels),
        )
        optimizer = self.trainer.optimizers[0]
        self.log(
            "learning_rate",
            float(optimizer.param_groups[0]["lr"]),
            sync_dist=False,
            on_step=False,
            on_epoch=True,
        )

    def configure_optimizers(self) -> torch.optim.Optimizer:
        # ClanControllerRestore replaces this placeholder from controller state.
        return torch.optim.SGD(self.parameters(), lr=9.0, momentum=0.9)


def _load_data() -> tuple[TensorDataset, TensorDataset]:
    dataset = load_iris()
    train_features, validation_features, train_labels, validation_labels = train_test_split(
        dataset.data,
        dataset.target,
        test_size=VALIDATION_SAMPLES,
        random_state=41,
        stratify=dataset.target,
    )
    scaler = StandardScaler().fit(train_features)
    train_features = scaler.transform(train_features)
    validation_features = scaler.transform(validation_features)
    train_dataset = TensorDataset(
        torch.tensor(train_features, dtype=torch.float32),
        torch.tensor(train_labels, dtype=torch.long),
    )
    validation_dataset = TensorDataset(
        torch.tensor(validation_features, dtype=torch.float32),
        torch.tensor(validation_labels, dtype=torch.long),
    )
    return train_dataset, validation_dataset


def train_member(config: dict[str, Any]) -> None:
    session = ClanTuneSession(config)
    controller = ClanController(
        member_id=session.member_id,
        population_size=session.population_size,
        initial_config={"lr": (0.01, 0.12)[session.member_id]},
        mutations={
            "lr": MutationSpec(
                standard_deviation=0.025,
                geometry="linear",
                minimum=0.002,
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
            "fitness": "validation_loss",
            "validation_accuracy": "validation_accuracy",
            "learning_rate": "learning_rate",
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
        max_epochs=20,
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
        deterministic=True,
    )
    train_dataset, validation_dataset = _load_data()
    train_loader = DataLoader(
        train_dataset,
        batch_size=12,
        shuffle=True,
        generator=torch.Generator().manual_seed(101),
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=15,
        sampler=replicated_sampler(validation_dataset),
    )
    with tune_checkpoint_path() as checkpoint_path:
        trainer.fit(
            IrisClassifier(),
            train_dataloaders=train_loader,
            val_dataloaders=validation_loader,
            ckpt_path=checkpoint_path,
        )


def run_experiment(storage_path: Path) -> dict[str, Any]:
    scheduler = ClanBasedTraining(
        population_size=POPULATION_SIZE,
        metric="fitness",
        mode="min",
        perturbation_interval=1,
    )
    started = time.perf_counter()
    ray.init(num_cpus=POPULATION_SIZE, include_dashboard=False, ignore_reinit_error=True)
    try:
        results = tune.Tuner(
            tune.with_resources(train_member, {"cpu": 1}),
            param_space={"trial_seed": tune.grid_search([17, 23])},
            run_config=tune.RunConfig(
                storage_path=str(storage_path),
                stop={"training_iteration": REPORTS_PER_TRIAL},
                checkpoint_config=tune.CheckpointConfig(num_to_keep=REPORTS_PER_TRIAL),
                failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
                verbose=0,
            ),
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                max_concurrent_trials=POPULATION_SIZE,
                reuse_actors=False,
            ),
        ).fit()
        errors = [str(result.error) for result in results if result.error is not None]
        member_results = [
            {
                "trial_path": result.path,
                "validation_loss": float(result.metrics["fitness"]),
                "validation_accuracy": float(result.metrics["validation_accuracy"]),
                "learning_rate": float(result.metrics["learning_rate"]),
            }
            for result in results
        ]
    finally:
        ray.shutdown()

    report = {
        "dataset": {
            "name": "Fisher Iris",
            "source": "sklearn.datasets.load_iris (UCI dataset 53)",
            "train_samples": TRAIN_SAMPLES,
            "validation_samples": VALIDATION_SAMPLES,
            "features": 4,
            "classes": 3,
        },
        "round_policy": {
            "population_size": POPULATION_SIZE,
            "reports_per_trial": REPORTS_PER_TRIAL,
            "completed_transitions": len(scheduler.selection_path),
            "fitness": "validation cross-entropy, minimized",
            "mutated_values": ["learning rate"],
        },
        "compute": {
            "accelerator": "CPU",
            "concurrent_cpus": POPULATION_SIZE,
            "elapsed_seconds": time.perf_counter() - started,
        },
        "errors": errors,
        "members": member_results,
        "selection_path": list(scheduler.selection_path),
        "limitations": [
            "Iris is very small and easy; it cannot establish general optimizer-policy value.",
            "The population has only two members and tunes only learning rate.",
            "The experiment has no fixed-schedule or ordinary PBT comparison.",
            "CPU and Gloo evidence does not qualify GPU or multi-node behavior.",
        ],
    }
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "iris_clan_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--storage-path",
        type=Path,
        default=Path("/tmp/clan-based-tuning-iris"),
    )
    report = run_experiment(parser.parse_args().storage_path)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
