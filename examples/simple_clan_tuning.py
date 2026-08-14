"""Minimal Ray Tune + Lightning Clan Tuning example.

The important userspace boundary is intentionally visible: after a selected parent
checkpoint is restored, this file explicitly reapplies the newly assigned Tune genome to
the inherited optimizer state. ClanBasedTuning never interprets or applies those values.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import lightning.pytorch as pl
import torch
from ray import tune
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback
from clan_based_tuning import MutationSpec

POPULATION_SIZE = 2
CHECKPOINT_FILENAME = "checkpoint.ckpt"


class ScalarModel(pl.LightningModule):
    """Tiny model whose optimizer learning rate is controlled by the Tune genome."""

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
        self.log("lr", self.optimizer.param_groups[0]["lr"])

    def configure_optimizers(self):
        return self.optimizer


def apply_genome(optimizer, genome):
    """Apply this member's current Tune genome to inherited optimizer state.

    This is ordinary user code. CBT neither calls this function nor knows that ``lr``
    names an optimizer parameter-group field.
    """

    for param_group in optimizer.param_groups:
        param_group["lr"] = genome["lr"]


def train(genome):
    """Run one Tune function member using the normal PBT restore/application pattern."""

    torch.set_num_threads(1)
    model = ScalarModel(genome)
    checkpoint = tune.get_checkpoint()

    # Lightning performs its complete model/optimizer/loop restore inside trainer.fit().
    # Keep a member-local copy of the inherited checkpoint alive for the entire fit so
    # user code can update the optimizer state that Lightning will restore.
    with tempfile.TemporaryDirectory() as local_checkpoint_dir:
        checkpoint_path = None
        if checkpoint is not None:
            restored_dir = checkpoint.to_directory(local_checkpoint_dir)
            checkpoint_path = Path(restored_dir, CHECKPOINT_FILENAME)
            state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

            # Restore the selected parent's optimizer history first.
            model.optimizer.load_state_dict(state["optimizer_states"][0])

            # USERSPACE APPLICATION: inject this member's newly assigned genome.
            apply_genome(model.optimizer, genome)

            # Lightning owns the final full-state restore. Put the user's updated
            # optimizer state into this local checkpoint copy before passing ckpt_path.
            state["optimizer_states"][0] = model.optimizer.state_dict()
            torch.save(state, checkpoint_path)

        data = DataLoader(TensorDataset(torch.tensor([0.0])), batch_size=1)
        trainer = pl.Trainer(
            accelerator="cpu",
            devices=1,
            strategy=ClanDDPStrategy(),
            callbacks=[ClanTuneReportCallback(extra_metrics=["lr"])],
            max_epochs=100,
            num_sanity_val_steps=0,
            logger=False,
            enable_checkpointing=False,
            enable_model_summary=False,
            enable_progress_bar=False,
        )
        trainer.fit(
            model,
            train_dataloaders=data,
            val_dataloaders=data,
            ckpt_path=str(checkpoint_path) if checkpoint_path is not None else None,
        )


def main():
    scheduler = ClanScheduler(
        population_size=POPULATION_SIZE,
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
    )

    results = tune.Tuner(
        tune.with_resources(
            scheduler.wrap(train),
            {"cpu": 1},
        ),
        param_space={
            "lr": tune.grid_search([0.1, 0.2]),
        },
        tune_config=tune.TuneConfig(
            scheduler=scheduler,
            max_concurrent_trials=POPULATION_SIZE,
        ),
        run_config=tune.RunConfig(
            stop={"training_iteration": 2},
        ),
    ).fit()

    for result in results:
        print(
            result.path,
            "val_loss=",
            result.metrics["val_loss"],
            "lr=",
            result.metrics["lr"],
        )


if __name__ == "__main__":
    main()
