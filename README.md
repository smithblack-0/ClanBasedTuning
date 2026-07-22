# ClanBasedTuning

ClanBasedTuning connects synchronous Ray Population Based Training to
Lightning's native DDP strategy lifecycle.

Each Ray Tune trial remains an ordinary trial with its own model trajectory,
optimizer state, configuration, checkpoint, and lineage. During training, the
trials join one PyTorch DDP process group. PyTorch performs its normal optimized
gradient reduction; each member then applies the common gradient through its own
optimizer state and hyperparameters.

## Design

The public API follows the two framework construction points directly:

- `ClanBasedTraining(...)` is the driver-side Ray scheduler.
- `make_clan_lightning_plugins(config, ...)` runs inside a Tune trial and
  returns the concrete Lightning strategy, cluster-environment plugin, and Ray
  reporting callback.
- `prepare_clan_trainer(trainer)` validates the explicit composition without
  injecting or replacing anything.
- `tune_checkpoint_path()` keeps Ray's materialized checkpoint alive while
  Lightning restores it.
- `replicated_sampler(dataset)` configures PyTorch's built-in
  `DistributedSampler` so every member evaluates the same examples.

Ray owns PBT scoring, mutation, checkpoint selection and cloning, pause, resume,
and trial restoration. Lightning owns the training loop and model transform.
PyTorch DDP owns gradient bucketing and collectives. ClanBasedTuning owns only
the seams needed to make those native lifecycles describe one cross-trial clan.

There is no package-owned `TuneConfig`, `RunConfig`, model wrapper, optimizer
schema, or training facade.

## Basic usage

```python
from lightning import Trainer
from ray import tune

from clan_based_tuning import (
    ClanBasedTraining,
    make_clan_lightning_plugins,
    prepare_clan_trainer,
    tune_checkpoint_path,
)

scheduler = ClanBasedTraining(
    population_size=4,
    metric="fitness",
    mode="min",
    perturbation_interval=4,
    hyperparam_mutations={
        "lr": tune.loguniform(1e-5, 1e-2),
        "weight_decay": tune.loguniform(1e-6, 1e-1),
    },
)


def train(config):
    model = MyLightningModule(config)
    clan = make_clan_lightning_plugins(
        config,
        metrics={"fitness": "val_loss"},
    )

    trainer = Trainer(
        accelerator="gpu",
        devices=1,
        num_nodes=1,
        strategy=clan.strategy,
        plugins=[clan.environment],
        callbacks=[clan.report_callback],
        enable_checkpointing=False,
    )
    prepare_clan_trainer(trainer)

    with tune_checkpoint_path() as checkpoint_path:
        trainer.fit(model, datamodule=MyDataModule(), ckpt_path=checkpoint_path)


tuner = tune.Tuner(
    tune.with_resources(train, {"gpu": 1}),
    param_space={
        "lr": tune.loguniform(1e-5, 1e-2),
        "weight_decay": tune.loguniform(1e-6, 1e-1),
    },
    tune_config=tune.TuneConfig(
        scheduler=scheduler,
        num_samples=4,
        max_concurrent_trials=4,
        reuse_actors=False,
    ),
    run_config=tune.RunConfig(
        stop={"training_iteration": 20},
        failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
    ),
)
tuner.fit()
```

The complete CPU example in
[`examples/native_clan_tuning.py`](examples/native_clan_tuning.py) can be run
without a GPU.

## Optimizer reconciliation

Ray's current trial config is authoritative for tuned hyperparameters, while an
exploited checkpoint supplies the source member's optimizer moments and other
state. After Lightning loads that state, ClanBasedTuning calls an injected
optimizer strategy to reconcile the live optimizer with the current config.

The default strategy supports exactly one optimizer with one parameter group.
It copies every top-level config value whose name already exists in the group:

```python
config = {"lr": 3e-4, "weight_decay": 0.01, "batch_size": 128}
```

For AdamW this updates `lr` and `weight_decay` and ignores `batch_size`. It never
touches `params`.

More complex layouts remain explicit user code:

```python
def apply_two_groups(optimizers, config):
    if len(optimizers) != 1 or len(optimizers[0].param_groups) != 2:
        raise ValueError("Expected one optimizer with two parameter groups")
    optimizers[0].param_groups[0]["lr"] = config["encoder_lr"]
    optimizers[0].param_groups[1]["lr"] = config["head_lr"]


clan = make_clan_lightning_plugins(
    config,
    metrics={"fitness": "val_loss"},
    apply_optimizer_strategy=apply_two_groups,
)
```

This function is called after optimizer construction and again after checkpoint
restore. Multiple optimizers, tuple fields such as Adam betas, aliases, and
transformations can be supported by supplying an appropriate function; they are
not part of the clan's durable identity.

## Data and metric contract

Training loaders should retain Lightning's normal distributed sampling. For
fitness evaluation, attach `replicated_sampler(dataset)` to the validation
loader so every member sees the same examples. Log member fitness with
`sync_dist=False`; synchronizing the metric would erase the member differences
that PBT needs to rank.

## Current limits

The initial implementation requires:

- synchronous PBT;
- the complete population resident concurrently;
- one Lightning process/device and one Ray resource bundle per trial;
- compatible model, buffer, optimizer-class, and parameter-group topology;
- fixed world size within a training window;
- no independent member failure recovery or member-local early termination;
- `init_sync=False` and `broadcast_buffers=False` so DDP does not erase member
  divergence.

The built-in optimizer strategy has the narrower one-optimizer/one-group limit;
that is not a fundamental restriction of Clan Based Training.

See [`docs/engineering/native_trial_build_contract.md`](docs/engineering/native_trial_build_contract.md)
for the detailed ownership and lifecycle contract.

The consolidated product model, intended support levels, and preliminary
rollout are developed in
[`docs/product_roadmap.md`](docs/product_roadmap.md). The document is a roadmap
draft, not a certification of the current implementation.

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

The framework-contract suite includes a two-process CPU exploit/restart probe
and a native Ray Tune/PBT cycle.
