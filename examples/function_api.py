"""Runnable two-member CPU example for the public Clan Tune function API.

From a repository checkout::

    python -m pip install -e .
    python examples/function_api.py

Ray supplies the current genome directly to ``train``. ``ScalarModel.on_train_start`` applies
that genome to the real optimizer after Lightning has restored any selected checkpoint. The
operation is intentionally visible in user code because genome meaning/application is not a
ClanBasedTuning responsibility.
"""

import tempfile
from pathlib import Path

import lightning.pytorch as pl
import torch
from ray import tune
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback


class ScalarModel(pl.LightningModule):
    """Keep the public ownership boundary visible with the smallest useful Lightning model.

    The model stores the Tune genome and owns the optimizer. Nothing in CBT knows that ``lr``
    is an optimizer field; that mapping exists only in this userspace class.
    """

    def __init__(self, genome: dict[str, float]) -> None:
        super().__init__()
        self.genome = genome
        self.weight = torch.nn.Parameter(torch.tensor(1.0))
        self.optimizer = torch.optim.SGD(
            self.parameters(),
            lr=genome["lr"],
            momentum=0.9,
        )

    def on_train_start(self) -> None:
        """Apply the child genome only after Lightning has restored inherited optimizer state.

        This ordering is the key userspace contract: checkpoint restore supplies the selected
        parent's model/optimizer history, then user code applies the receiving member's new
        policy values to that live optimizer.
        """

        # USERSPACE. Lightning has restored the selected optimizer history before this hook.
        # CBT does not know what "lr" means and does not perform, wrap, or infer this edit.
        for param_group in self.optimizer.param_groups:
            param_group["lr"] = self.genome["lr"]

    def training_step(self, batch: tuple[torch.Tensor], batch_index: int) -> torch.Tensor:
        """Use a deliberately transparent gradient so the example foregrounds CBT mechanics."""

        del batch, batch_index
        return self.weight

    def validation_step(self, batch: tuple[torch.Tensor], batch_index: int) -> None:
        """Report local candidate fitness plus evidence that userspace applied the genome."""

        del batch, batch_index
        self.log("val_loss", self.weight.square())
        self.log("lr_seen", self.optimizer.param_groups[0]["lr"])

    def configure_optimizers(self) -> torch.optim.Optimizer:
        """Hand Lightning the user-owned optimizer whose momentum history CBT later inherits."""

        return self.optimizer


def train(genome: dict[str, float]) -> None:
    """Implement one Clan member as an ordinary Tune function and ordinary Lightning restore.

    Tune checkpoint materialization is kept alive only long enough for ``Trainer.fit`` to
    restore it. There is no CBT-specific trainable wrapper and no checkpoint surgery; the
    receiving genome is applied later by the model's normal ``on_train_start`` hook.
    """

    torch.set_num_threads(1)
    model = ScalarModel(genome)
    checkpoint = tune.get_checkpoint()

    # Keep Tune's local checkpoint materialization alive until Lightning finishes restoration.
    # There is no userspace checkpoint rewriting: application happens against the restored
    # optimizer in ScalarModel.on_train_start.
    with tempfile.TemporaryDirectory() as local_checkpoint_dir:
        checkpoint_path = None
        if checkpoint is not None:
            checkpoint_dir = checkpoint.to_directory(local_checkpoint_dir)
            checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")

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


def main() -> None:
    """Compose the three public CBT objects with Tune while keeping variation scientifically valid.

    The only mutated field is learning rate, which changes the optimizer update after the
    common DDP gradient has already been computed. Architecture, data, forward computation,
    and loss remain identical across members.
    """

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
    # qualifies; model architecture, training data, forward behavior, and loss do not.
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
