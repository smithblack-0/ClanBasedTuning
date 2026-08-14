"""Minimal runnable Clan Tuning example using the Ray Tune function API.

Install the optional integration first:

    python -m pip install -e '.[ray]'

This example intentionally keeps genome application in userspace. ClanBasedTuning supplies
new genome values through Ray Tune; the application function below belongs to this program.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import lightning.pytorch as pl
import torch
from ray import tune
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import (
    ClanDDPStrategy,
    ClanScheduler,
    ClanTuneReportCallback,
    MutationSpec,
)


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


def apply_genome(optimizer, genome):
    """Userspace policy for interpreting this program's genome."""

    for param_group in optimizer.param_groups:
        param_group["lr"] = genome["lr"]


def train(genome):
    """One Ray Tune member invocation."""

    torch.set_num_threads(1)
    model = ScalarModel(genome)
    checkpoint = tune.get_checkpoint()

    # The local materialization must remain alive until Lightning finishes restoring and
    # training. It is a per-member temporary copy, not another persistent CBT checkpoint.
    local_checkpoint = tempfile.TemporaryDirectory()
    checkpoint_path = None

    if checkpoint is not None:
        checkpoint_dir = checkpoint.to_directory(local_checkpoint.name)
        checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

        # USERSPACE: preserve inherited optimizer history, then apply this member's newly
        # assigned genome. CBT neither calls nor knows about this function.
        model.optimizer.load_state_dict(state["optimizer_states"][0])
        apply_genome(model.optimizer, genome)

        # Lightning performs the final full-state restore inside trainer.fit(). Put the
        # userspace optimizer change into this member's local checkpoint copy first.
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
        devices=1,
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

    local_checkpoint.cleanup()


def main():
    population_size = 2
    scheduler = ClanScheduler(
        population_size=population_size,
        metric="val_loss",
        mode="min",
        mutations={
            "lr": MutationSpec(
                standard_deviation=0.15,
                geometry="log",
                minimum=0.02,
                maximum=0.5,
            )
        },
        seed=7,
        join_timeout_s=60.0,
    )

    results = tune.Tuner(
        tune.with_resources(scheduler.wrap(train), {"cpu": 1}),
        param_space={"lr": tune.grid_search([0.1, 0.2])},
        tune_config=tune.TuneConfig(
            scheduler=scheduler,
            max_concurrent_trials=population_size,
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
