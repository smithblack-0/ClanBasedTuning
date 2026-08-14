# Public API

Status: current function-API surface on the active integration branch

## Ordinary use

ClanBasedTuning follows Ray Tune's function-trainable PBT shape. The Tune configuration
passed to the function is the member's current **genome**. CBT selects a parent,
constructs the next genomes, and asks Ray to resume every member from the selected
checkpoint. The training function decides what the genome means and applies it itself.

CBT does **not** inspect an optimizer, infer optimizer fields, or provide an optimizer
application callback.

A simple Lightning use looks like this:

```python
from pathlib import Path
import tempfile

import lightning.pytorch as pl
import torch
from ray import tune

from clan_based_tuning import MutationSpec
from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback

CHECKPOINT_FILENAME = "checkpoint.ckpt"


class Model(pl.LightningModule):
    def __init__(self, genome):
        super().__init__()
        self.network = ...

        # The first generation uses the initial genome directly.
        self.optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=genome["lr"],
            weight_decay=genome["weight_decay"],
        )

    def training_step(self, batch, batch_index):
        ...

    def validation_step(self, batch, batch_index):
        ...
        self.log("val_loss", loss)

    def configure_optimizers(self):
        return self.optimizer


def apply_genome(optimizer, genome):
    # USERSPACE. CBT never calls or interprets this function.
    for param_group in optimizer.param_groups:
        param_group["lr"] = genome["lr"]
        param_group["weight_decay"] = genome["weight_decay"]


def train(genome):
    model = Model(genome)
    checkpoint = tune.get_checkpoint()

    # Keep the temporary directory alive for the complete Trainer invocation.
    local_checkpoint = tempfile.TemporaryDirectory()
    checkpoint_path = None

    if checkpoint is not None:
        checkpoint_dir = checkpoint.to_directory(local_checkpoint.name)
        checkpoint_path = Path(checkpoint_dir, CHECKPOINT_FILENAME)
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

        # Restore the selected parent's optimizer history.
        model.optimizer.load_state_dict(state["optimizer_states"][0])

        # Apply THIS member's newly assigned genome explicitly in user code.
        apply_genome(model.optimizer, genome)

        # Lightning owns the final full-state restore through ckpt_path, so place the
        # user's updated optimizer state into this member's local checkpoint copy.
        state["optimizer_states"][0] = model.optimizer.state_dict()
        torch.save(state, checkpoint_path)

    trainer = pl.Trainer(
        accelerator="auto",
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

The application block is deliberately explicit. Loading the parent optimizer state first
preserves momentum and other optimizer history; applying the current genome afterward
replaces only whatever the user's application function chooses to replace. The local
checkpoint rewrite exists because Lightning performs the final model, optimizer, loop,
and training-progress restore inside `trainer.fit(..., ckpt_path=...)`.

A user with multiple optimizers, parameter-group-specific settings, a custom optimizer,
or non-optimizer genome fields writes the corresponding application logic. CBT does not
need to understand it.

## Tune setup

The scheduler carries Clan-specific cohort context beside the function without inserting
private keys into the user's genome dictionary.

```python
scheduler = ClanScheduler(
    population_size=4,
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

result = tune.Tuner(
    tune.with_resources(
        scheduler.wrap(train),
        {"cpu": 1, "gpu": 1},  # resources for each Clan member
    ),
    param_space={
        "lr": tune.loguniform(1e-4, 1e-3),
        "weight_decay": tune.loguniform(1e-5, 1e-2),
    },
    tune_config=tune.TuneConfig(
        scheduler=scheduler,
        num_samples=4,
        max_concurrent_trials=4,
    ),
).fit()
```

`with_resources` describes one Tune trial/member, so the example above requires four GPUs
and at least four CPUs for the complete four-member Clan. For the initial DDP path, the
complete Clan must be resident together: the Tune run must permit `population_size`
concurrent trials and the cluster must be able to satisfy all of their per-member resource
requests at once. Each wrapped function still receives only the ordinary Ray `genome`
mapping supplied by Tune.

## `ClanScheduler`

`ClanScheduler` uses Ray's synchronous Population Based Training execution lifecycle but
replaces the population policy with Clan Tuning's single-parent transition.

At each Tune report boundary it:

1. verifies one report from every stable Clan member;
2. independently selects the same winner chosen by the workers;
3. retains that member as the sole parent;
4. verifies the selected checkpoint's producer metadata against the selected member and
   active controlled genome;
5. lets Ray assign the parent's reported checkpoint to every resumed member;
6. leaves the winning member's genome unchanged; and
7. clones the winning genome to every losing target and applies the declared
   `MutationSpec` values to the controlled keys.

Mutation keys identify scheduler-controlled **genome values**, not optimizer fields. CBT
never asks what a key means to the user's program.

`ClanScheduler.wrap(train)` is required for the initial function path. It supplies stable
member identity and DDP rendezvous context without changing the dictionary passed to
`train(genome)`.

## `ClanDDPStrategy`

`ClanDDPStrategy` is an ordinary Lightning `DDPStrategy` specialized only for the
cross-trial Clan topology.

It does not select a process-group backend. With no backend argument, Lightning/PyTorch
choose their ordinary backend for the selected accelerator. A user who deliberately wants
a particular supported backend may use the ordinary argument:

```python
strategy = ClanDDPStrategy(process_group_backend="...")
```

The strategy supplies the externally assigned rank/world-size/rendezvous facts, exposes
the complete Clan to Lightning's distributed sampler, and disables DDP's per-forward
buffer broadcast so member-local updates are not silently overwritten.

For CBT round checkpoints, every rank enters Lightning's normal checkpoint construction
and barrier. Only the selected rank delegates the checkpoint to Lightning's configured
`CheckpointIO`. Losing ranks therefore construct transient checkpoint dictionaries in
memory but write no CBT checkpoint file.

Ordinary user-triggered Lightning checkpoint calls outside that scoped CBT operation keep
Lightning's normal behavior.

## `ClanTuneReportCallback`

`ClanTuneReportCallback` closes one round at Lightning validation end. Lightning's
validation cadence therefore determines round frequency; CBT does not add another
training-progress clock.

The callback:

1. reads the local fitness metric;
2. exchanges one scalar fitness per member through the already-established DDP process
   group;
3. applies the framework-independent deterministic winner rule;
4. has all ranks enter Lightning checkpoint construction while only the winner writes;
5. reports ordinary metrics from every member to Tune; and
6. reports a Ray checkpoint only from the selected member.

The callback never applies the genome and never touches optimizer hyperparameters.

By default the Lightning metric and Tune metric have the same name declared on
`ClanScheduler`. `lightning_metric=` may name a different Lightning metric, and
`extra_metrics=` may expose additional metrics to Tune.

## Checkpoint storage

A Clan round produces one persistent CBT continuation checkpoint, independent of
population size. Ray's synchronous PBT transition then references that selected
checkpoint for every target member rather than asking every member to persist its own
copy.

Users may deliberately configure additional Lightning checkpoints for their own purposes;
those are separate from CBT's one-parent continuation and naturally consume additional
storage.

## `MutationSpec`

`MutationSpec` is framework-independent and publicly exported.

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
Tune scheduler owns the random stream used to apply these mutations.

## `ClanController`

`ClanController` remains the small framework-independent worker decision primitive behind
the reporting integration. It stores one local fitness, performs one injected complete
population exchange, caches the checkpoint-source decision, and exposes the selected
member identity after resolution.

Ordinary Lightning/Tune users do not construct it themselves; the reporting callback
provides the established DDP exchange and uses it internally. Direct construction remains
useful for tests and advanced composition.
