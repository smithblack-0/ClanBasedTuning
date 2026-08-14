"""Runnable two-member CPU example for the public Clan Tune function API.

From a repository checkout:

    python -m pip install '.[ray]'
    python examples/function_api.py

Ray supplies the current genome directly to ``train``. The optimizer edits below are
intentionally inline because they are application policy, not ClanBasedTuning behavior.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import lightning.pytorch as pl
import torch
from ray import tune
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback


class ScalarModel(pl.LightningModule):
    """Tiny model whose learning rate produces visible member divergence."""

    def __init__(self, genome):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(1.0))
        self.optimizer = torch.optim.SGD(
            self.parameters(),
            lr=genome["lr"],
            momentum=0.9,
        )

    def training_step(self, batch, batch_index):
        del batch, batch_index
        return self.weight

    def validation_step(self, batch, batch_index):
        del batch, batch_index
        self.log("val_loss", self.weight.square())
        self.log("lr_seen", self.optimizer.param_groups[0]["lr"])

    def configure_optimizers(self):
        return self.optimizer


def train(genome):
    """One ordinary Ray Tune function trial, representing one Clan member."""

    torch.set_num_threads(1)
    model = ScalarModel(genome)
    checkpoint = tune.get_checkpoint()

    # Keep the local checkpoint copy alive until Lightning finishes restoring and training.
    # This copy is transient; only the selected member reports a persistent CBT checkpoint.
    with tempfile.TemporaryDirectory() as local_checkpoint_dir:
        checkpoint_path = None

        if checkpoint is not None:
            checkpoint_dir = checkpoint.to_directory(local_checkpoint_dir)
            checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")
            state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

            # USERSPACE. Inherit the selected optimizer history, then visibly apply this
            # member's newly assigned genome. CBT does not know what "lr" means and does
            # not perform, wrap, or infer these operations.
            model.optimizer.load_state_dict(state["optimizer_states"][0])
            for param_group in model.optimizer.param_groups:
                param_group["lr"] = genome["lr"]

            # trainer.fit(ckpt_path=...) performs Lightning's complete state restoration.
            # Put the userspace optimizer edit into this member's local copy so the newly
            # assigned genome remains authoritative after that restore.
            state["optimizer_states"][0] = model.optimizer.state_dict()
            torch.save(state, checkpoint_path)

        training_data = DataLoader(
            TensorDataset(torch.tensor([0.0, 1.0, 2.0, 3.0])),
            batch_size=1,
            shuffle=False,
        )
        validation_data = DataLoader(
            TensorDataset(torch.tensor([0.0, 1.0, 2.0, 3.0])),
            batch_size=1,
            shuffle=False,
        )

        trainer = pl.Trainer(
            accelerator="cpu",
            strategy=ClanDDPStrategy(),
            callbacks=[ClanTuneReportCallback(extra_metrics=["lr_seen"])],
            max_epochs=100,
            logger=False,
            enable_checkpointing=False,
            enable_model_summary=False,
            enable_progress_bar=False,
            limit_train_batches=1,
        )
        trainer.fit(
            model,
            train_dataloaders=training_data,
            val_dataloaders=validation_data,
            ckpt_path=str(checkpoint_path) if checkpoint_path is not None else None,
        )


def main():
    population_size = 2
    scheduler = ClanScheduler(
        population_size=population_size,
        mutations={
            "lr": {
                "standard_deviation": 0.15,
                "geometry": "log",
                "minimum": 0.02,
                "maximum": 0.5,
            }
        },
        seed=7,
        join_timeout_s=60.0,
    )

    # Valid Clan variation is applied after the common gradient is computed. Learning rate
    # qualifies; model architecture, training data, and forward/loss behavior do not.
    results = tune.Tuner(
        tune.with_resources(train, {"cpu": 1}),
        param_space={"lr": tune.grid_search([0.1, 0.2])},
        tune_config=tune.TuneConfig(
            scheduler=scheduler,
            metric="val_loss",
            mode="min",
        ),
        run_config=tune.RunConfig(
            name="clan-function-api-example",
            stop={"training_iteration": 3},
        ),
    ).fit()

    print("Final member genomes and reported learning rates:")
    for result in results:
        print(
            {
                "genome": result.config,
                "lr_seen": result.metrics["lr_seen"],
                "val_loss": result.metrics["val_loss"],
            }
        )


if __name__ == "__main__":
    main()
