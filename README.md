# ClanBasedTuning

ClanBasedTuning integrates Clan Tuning with Ray Tune, Lightning, and PyTorch. A Clan is a
population of Tune trials that shares each training gradient through one Lightning/PyTorch
DDP world while retaining member-local optimizer state. At a validation boundary one member
is selected as the sole training continuation, and every next member receives an independent
mutation of that selected parent's Tune config.

The project is pre-release. The currently targeted complete path is one CPU node with two
concurrent members; GPU/NCCL, multi-node execution, active-collective failure recovery, and
model-sharded execution remain separate qualification work.

## Install

From a checkout:

```bash
git clone https://github.com/smithblack-0/ClanBasedTuning.git
cd ClanBasedTuning
python -m pip install -e .
```

For development:

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Ray, Lightning, and PyTorch are core runtime dependencies because the package's public
surface is their integration. Dependency metadata intentionally uses minimum versions rather
than a point-version Ray pin. Support claims remain limited to versions actually qualified;
Ray-specific low-level checkpoint transfer is isolated in one compatibility module so an
upstream change requires a local adapter repair rather than a scheduler redesign.

## Minimal function API

Ray supplies the current genome/config directly to the ordinary user function. CBT selects
and mutates that dictionary but never interprets or applies its values.

A receiving Lightning model can apply the current genome in `on_train_start`. Lightning has
already restored optimizer/training state before this hook, so the user's edit applies to the
real inherited optimizer without rewriting Lightning's checkpoint payload.

```python
from pathlib import Path
import tempfile

import lightning.pytorch as pl
from ray import tune
import torch

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback


class Model(pl.LightningModule):
    def __init__(self, genome):
        super().__init__()
        self.genome = genome
        self.network = ...
        self.optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=genome["lr"],
            weight_decay=genome["weight_decay"],
        )

    def on_train_start(self):
        # USERSPACE. Lightning restored optimizer history before this hook.
        for group in self.optimizer.param_groups:
            group["lr"] = self.genome["lr"]
            group["weight_decay"] = self.genome["weight_decay"]

    def training_step(self, batch, batch_index):
        ...

    def validation_step(self, batch, batch_index):
        loss = ...
        self.log("val_loss", loss)  # keep candidate fitness member-local

    def configure_optimizers(self):
        return self.optimizer


def train(genome):
    model = Model(genome)
    checkpoint = tune.get_checkpoint()

    with tempfile.TemporaryDirectory() as local_checkpoint_dir:
        checkpoint_path = None
        if checkpoint is not None:
            checkpoint_dir = checkpoint.to_directory(local_checkpoint_dir)
            checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")

        trainer = pl.Trainer(
            strategy=ClanDDPStrategy(),
            callbacks=[ClanTuneReportCallback()],
            enable_checkpointing=False,
            ...,
        )
        trainer.fit(
            model,
            train_dataloaders=train_loader,
            val_dataloaders=val_loader,
            ckpt_path=str(checkpoint_path) if checkpoint_path is not None else None,
        )


population_size = 4
scheduler = ClanScheduler(
    population_size=population_size,
    mutations={
        "lr": {
            "standard_deviation": 0.20,
            "geometry": "log",
            "minimum": 1e-5,
            "maximum": 1e-2,
        },
        "weight_decay": {
            "standard_deviation": 0.20,
            "geometry": "log",
            "minimum": 1e-6,
            "maximum": 1e-1,
        },
    },
)

results = tune.Tuner(
    tune.with_resources(train, {"gpu": 1}),
    param_space={
        "lr": tune.loguniform(1e-4, 1e-3),
        "weight_decay": tune.loguniform(1e-5, 1e-2),
    },
    tune_config=tune.TuneConfig(
        scheduler=scheduler,
        metric="val_loss",
        mode="min",
        num_samples=population_size,
    ),
).fit()
```

One Ray trial is one Clan member and one Lightning process/device. Ray owns per-trial
resources; ordinary users should not duplicate that topology with `Trainer(devices=...)`.
The complete Clan must fit concurrently because all members participate in one live DDP
world.

## Genome validity

The software boundary is generic, but the Clan Tuning algorithm is not. A varying choice
must be applied after the common gradient has been computed. Learning rate, weight decay,
momentum/betas, and similar optimizer-side update policy are the intended use. Varying model
architecture, training data, forward behavior, or loss would make members contribute
gradients for different training problems and is not valid Clan Tuning.

Candidate fitness must also remain member-local until CBT compares members. Do not
`sync_dist` the candidate fitness across the Clan.

## Restore an interrupted Tune run

ClanBasedTuning uses Ray's ordinary experiment restoration path:

```python
restored = tune.Tuner.restore(
    experiment_path,
    trainable=tune.with_resources(train, {"gpu": 1}),
    resume_unfinished=True,
    resume_errored=True,
)
results = restored.fit()
```

The runtime registry/coordinator is reconstructed from scheduler state when the Tune
experiment resumes; no CBT-specific restore API or trainable wrapper is required.

## Public components

- `ClanScheduler`: synchronous Clan generation scheduler using Tune's scheduler lifecycle.
  CBT owns the small single-parent transition instead of subclassing Ray's PBT internals.
- `ClanDDPStrategy`: Lightning DDP strategy joining independently launched Tune trials into
  one framework-managed DDP world while preserving training partitioning and comparable
  Lightning-managed validation.
- `ClanTuneReportCallback`: Lightning callback that gathers member-local fitness and reports
  the selected continuation through Tune.

A runnable CPU mechanics example is [`examples/function_api.py`](examples/function_api.py).
Detailed behavior and compatibility boundaries are in [`docs/api.md`](docs/api.md); current
qualification and repository readiness are in [`STATUS.md`](STATUS.md).
