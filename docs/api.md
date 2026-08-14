# Public API

Status: implemented initial Ray Tune function path

## Ordinary use

ClanBasedTuning follows Ray Tune's function-trainable shape. The dictionary passed to the
user function is the member's current **genome**. CBT selects the common parent
continuation and produces the next genomes; user code alone decides what a genome means
and how to use it.

CBT does not inspect optimizers, infer genome-key meanings, apply genomes, provide an
application callback, or run a post-load application hook.

A complete Lightning shape is:

```python
from pathlib import Path
import tempfile

import lightning.pytorch as pl
import torch
from ray import tune

from clan_based_tuning import (
    ClanDDPStrategy,
    ClanScheduler,
    ClanTuneReportCallback,
    MutationSpec,
)


class Model(pl.LightningModule):
    def __init__(self, genome):
        super().__init__()
        self.network = ...
        self.optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=genome["lr"],
            weight_decay=genome["weight_decay"],
        )

    def training_step(self, batch, batch_index):
        ...

    def validation_step(self, batch, batch_index):
        loss = ...
        self.log("val_loss", loss)

    def configure_optimizers(self):
        return self.optimizer


def apply_genome(optimizer, genome):
    # USERSPACE. This function is not part of CBT and CBT never calls it.
    for param_group in optimizer.param_groups:
        param_group["lr"] = genome["lr"]
        param_group["weight_decay"] = genome["weight_decay"]


def train(genome):
    model = Model(genome)
    checkpoint = tune.get_checkpoint()

    # Keep this local materialization alive for the Trainer invocation.
    local_checkpoint = tempfile.TemporaryDirectory()
    checkpoint_path = None

    if checkpoint is not None:
        checkpoint_dir = checkpoint.to_directory(local_checkpoint.name)
        checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

        # USERSPACE: inherit optimizer history, then apply this member's current genome.
        model.optimizer.load_state_dict(state["optimizer_states"][0])
        apply_genome(model.optimizer, genome)

        # Lightning will perform the final full-state restore. Put the user's changed
        # optimizer state into this member's local checkpoint copy before fit().
        state["optimizer_states"][0] = model.optimizer.state_dict()
        torch.save(state, checkpoint_path)

    trainer = pl.Trainer(
        devices=1,
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
```

The local checkpoint edit above is ordinary user code. It is one way to preserve
Lightning's full checkpoint restoration while ensuring the newly assigned genome wins
over the parent's optimizer hyperparameters. A user may choose another explicit
userspace mechanism. CBT has no application protocol to satisfy.

The qualified contract verifies that this pattern preserves the selected parent's model
state, optimizer history, and Lightning training progress while the user changes the
optimizer according to the newly received genome.

## Tune setup

`ClanScheduler.wrap(train)` adds hidden cohort/rendezvous context beside the function. It
does not add, remove, inspect, or rewrite keys in the dictionary passed to `train(genome)`.

```python
population_size = 4

scheduler = ClanScheduler(
    population_size=population_size,
    metric="val_loss",
    mode="min",
    mutations={
        "lr": MutationSpec(
            standard_deviation=0.20,
            geometry="log",
            minimum=1e-5,
            maximum=1e-2,
        ),
        "weight_decay": MutationSpec(
            standard_deviation=0.20,
            geometry="log",
            minimum=1e-6,
            maximum=1e-1,
        ),
    },
    seed=7,
)

results = tune.Tuner(
    tune.with_resources(
        scheduler.wrap(train),
        {"cpu": 1},
    ),
    param_space={
        "lr": tune.loguniform(1e-4, 1e-3),
        "weight_decay": tune.loguniform(1e-5, 1e-2),
    },
    tune_config=tune.TuneConfig(
        scheduler=scheduler,
        num_samples=population_size,
        max_concurrent_trials=population_size,
    ),
).fit()
```

For the initial path, all members must be resident concurrently. The cluster therefore
needs enough resources for `population_size` copies of the per-trial resource request.
Insufficient capacity cannot be time-multiplexed safely because the live members form one
DDP world.

## `ClanScheduler`

`ClanScheduler` specializes Ray's synchronous `PopulationBasedTraining` lifecycle. Ray
continues to own trial execution, pausing, checkpoint transfer, restart, and config
replacement.

At each completed round the scheduler:

1. waits for one result from every stable Clan member;
2. verifies stable member identity and one common generation boundary;
3. independently applies the same deterministic winner rule used by the workers;
4. makes the selected member the sole checkpoint source;
5. snapshots that selected member's current Tune config; and
6. gives **every** next member, including the selected member, an independent mutation of
   that same parent config.

Mutation keys are Tune-config keys. They are not optimizer fields from CBT's perspective.
The scheduler mutates values; the user's function decides what those values do.

`ClanScheduler.wrap(train)` is required for the initial integration because separate Tune
trials need hidden stable-member and DDP rendezvous context. The wrapped function still
receives the original Ray config argument unchanged.

## `ClanDDPStrategy`

`ClanDDPStrategy` is a Lightning `DDPStrategy` for one externally launched Tune trial per
Clan member.

It supplies the rank, world size, and rendezvous facts Lightning cannot infer across
independent Tune trials. It does not initialize a second process group or select a
backend. With no explicit backend argument, normal Lightning/PyTorch backend selection is
used. A user may still pass the ordinary Lightning option when deliberately required:

```python
strategy = ClanDDPStrategy(process_group_backend="...")
```

The strategy disables DDP's per-forward buffer broadcast so one member's later local
state is not silently copied over another member after divergence.

For Lightning-managed dataloaders, the strategy preserves ordinary DDP partitioning for
training and changes only Lightning's **automatically injected** validation sampler. At
validation and sanity-validation setup it supplies `num_replicas=1, rank=0`, so every Clan
member evaluates the complete held-out dataset instead of a rank shard. This lets diverged
candidates be compared on the same examples.

If the user explicitly supplies a `DistributedSampler`, Lightning does not auto-inject a
replacement and CBT leaves that sampler alone. Such an explicit sampler is therefore
userspace and must itself satisfy the intended evaluation semantics.

During a CBT round checkpoint, every member participates in Lightning checkpoint
construction and the normal `Trainer.save_checkpoint()` barrier. Only the selected rank
delegates the checkpoint to Lightning's `CheckpointIO`. Ordinary checkpoint calls outside
that scoped CBT operation keep Lightning's normal behavior.

## `ClanTuneReportCallback`

`ClanTuneReportCallback` closes a round at Lightning validation end.

It:

1. reads one local Lightning fitness metric;
2. gathers one scalar fitness from every member through the active Lightning strategy;
3. applies the shared deterministic selection rule locally;
4. has all members participate in Lightning checkpoint construction;
5. permits only the selected member to persist the CBT continuation; and
6. reports metrics from every trial while only the selected member reports a Ray
   checkpoint.

The callback has no genome argument and no genome-application behavior.

By default, the Lightning metric name is the same `metric` supplied to `ClanScheduler`.
`lightning_metric=` may select a different local Lightning metric. `extra_metrics=` can
forward additional callback metrics to Tune.

The fitness metric must remain member-local. In particular, user logging must not reduce
that metric across the Clan before CBT compares members.

## Checkpoint storage

A completed Clan round has one persistent CBT continuation checkpoint, independent of
population size. Losing members may transiently construct checkpoint dictionaries because
Lightning's distributed checkpoint boundary is collective, but they do not write or
report a CBT checkpoint.

Ray's synchronous PBT lifecycle then transfers the selected continuation to the next
members. The receiving user function gets that checkpoint from `tune.get_checkpoint()`.

Additional user-configured Lightning checkpoints are separate and consume whatever
storage the user deliberately configures.

## `MutationSpec`

`MutationSpec` is framework-independent:

```python
mutation = MutationSpec(
    standard_deviation=0.25,
    geometry="log",
    minimum=1e-5,
    maximum=1e-2,
)
```

`geometry="linear"` adds a Gaussian displacement. `geometry="log"` multiplies by the
exponential of the displacement. `minimum` and `maximum` clamp the resulting value. The
Clan scheduler owns the mutation random stream.

## `ClanController`

`ClanController` is the small framework-independent decision primitive used by the
Lightning reporting integration. It stores one local fitness, performs one injected
complete-population exchange, caches the checkpoint-source decision, and exposes the
resolved winner identity.

Ordinary Tune/Lightning users do not need to construct it. Direct construction remains
useful for framework-independent tests and advanced composition.

## Current support boundary

The complete function path is directly qualified on a single node with two concurrent CPU
members using Ray 2.56.1, Lightning 2.6.5, PyTorch 2.10.0, and Python 3.11. The package's
non-Ray tests also run on Python 3.13.

The qualified Lightning-managed data path proves that training remains rank-partitioned
while every member sees the same complete multi-example validation dataset, including
when that validation loader is first prepared for Lightning's normal sanity check.

The following are not yet support claims for the complete path:

- CUDA/NCCL;
- multi-node execution;
- actor reuse across generations;
- failure recovery after a member or distributed-collective failure;
- model-sharded Clan execution; or
- the semantics of explicitly user-supplied distributed validation samplers.

The candidate fitness metric must remain local until CBT's population exchange. Users who
replace Lightning's automatic validation sampling are responsible for preserving
comparable member evaluation.
