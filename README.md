# ClanBasedTuning

ClanBasedTuning integrates Clan Tuning with Ray Tune, Lightning, and PyTorch. A Clan is a
population of Tune trials that shares each training gradient through one Lightning/PyTorch
DDP world while retaining member-local optimizer state. At validation boundaries the best
member supplies the sole continuation checkpoint and every next member receives an
independent mutation of that selected parent's Tune config.

The project is still pre-release. The currently qualified complete path is two concurrent
CPU members on one node; GPU, multi-node, active-collective failure recovery, and
model-sharded execution remain explicit follow-up qualifications.

## Install from a checkout

Python 3.11 through 3.13 is supported by the package. The complete Ray/Lightning mechanics
path is currently qualified on Python 3.11.

```bash
git clone https://github.com/smithblack-0/ClanBasedTuning.git
cd ClanBasedTuning
python -m pip install '.[ray]'
```

For development:

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

A PyPI release, license declaration, and release process are not yet claimed. See
[`STATUS.md`](STATUS.md) for repository-readiness gaps rather than inferring production
readiness from the mechanics tests.

## Minimal function API

The user function receives an ordinary Ray Tune config dictionary. CBT selects and mutates
that dictionary but never interprets or applies its values.

```python
from pathlib import Path
import tempfile

import lightning.pytorch as pl
import torch
from ray import tune

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback


def train(genome):
    model = MyLightningModule(genome)
    checkpoint = tune.get_checkpoint()

    with tempfile.TemporaryDirectory() as local_checkpoint_dir:
        checkpoint_path = None

        if checkpoint is not None:
            checkpoint_dir = checkpoint.to_directory(local_checkpoint_dir)
            checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")
            state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

            # USERSPACE: inherit optimizer history, then apply the current genome visibly.
            model.optimizer.load_state_dict(state["optimizer_states"][0])
            for group in model.optimizer.param_groups:
                group["lr"] = genome["lr"]
                group["weight_decay"] = genome["weight_decay"]

            state["optimizer_states"][0] = model.optimizer.state_dict()
            torch.save(state, checkpoint_path)

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
    # One Ray trial is one Clan member and one Lightning process/device.
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

Ray owns per-trial resources. In ordinary use, do not duplicate that topology with
`Trainer(devices=...)`; Lightning's default resolves the one device made visible to each
trial. `ClanDDPStrategy` rejects a trial that resolves more than one Lightning process/device.
The whole Clan must fit concurrently because the members form one live DDP world.

For a fixed initial population, `grid_search` can define exactly `population_size` trials
without also setting `num_samples`. For a sampled initial population, set
`TuneConfig(num_samples=population_size)` as in ordinary Ray Tune.

### What may be in the genome?

The software boundary is deliberately generic, but the Clan Tuning algorithm is not. A
valid varying choice must be applied after the shared gradient has been computed. Learning
rate, weight decay, momentum, and similar optimizer-side policy are the intended use.
Changing model architecture, training data, the forward pass, or the loss would make the
members contribute gradients for different training problems and is not valid Clan Tuning.

The fitness metric must also remain member-local until CBT compares members. Do not
`sync_dist` the candidate fitness across the Clan.

## Restore an interrupted Tune run

ClanBasedTuning uses Ray's normal experiment restoration path. Re-create the same trainable
resource annotation and restore the experiment directory; the scheduler/runtime state is
re-established from the saved Tune experiment.

```python
restored = tune.Tuner.restore(
    experiment_path,
    trainable=tune.with_resources(train, {"gpu": 1}),
    resume_unfinished=True,
    resume_errored=True,
)
results = restored.fit()
```

The framework contract exercises this across a fresh Ray runtime after an intentional
post-checkpoint failure. See [`docs/qualification/function_api.md`](docs/qualification/function_api.md)
for the exact evidence boundary.

## Public components

- `ClanScheduler`: Ray synchronous-PBT specialization implementing the single-parent Clan
  generation transition and mutation policy.
- `ClanDDPStrategy`: Lightning DDP strategy that joins independently launched Tune trials
  into one framework-managed DDP world, preserves training partitioning, and replicates
  Lightning-managed validation.
- `ClanTuneReportCallback`: Lightning callback that compares member-local fitness and
  reports the selected continuation through Ray Tune.

A complete runnable CPU example is [`examples/function_api.py`](examples/function_api.py).
The detailed usage contract is [`docs/api.md`](docs/api.md). Architecture, support evidence,
and current readiness are indexed from [`docs/README.md`](docs/README.md).
