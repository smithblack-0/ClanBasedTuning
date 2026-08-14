# Public API

Status: implemented pre-release Ray Tune function path

## Mental model

A Clan run uses ordinary Ray Tune function trials and ordinary Lightning training. One Tune
trial is one Clan member and one Lightning process/device. The members form one
Lightning/PyTorch DDP world: training data remains partitioned and gradients are reduced in
the normal DDP way, but each member applies that shared gradient through its own optimizer
state and current Tune config. At validation end, CBT compares one member-local fitness
value from each member, selects one continuation, and Ray restarts the next generation from
that selected checkpoint with new sibling mutations of the selected config.

CBT owns selection, mutation, cohort identity, and the small Lightning/Ray integration seams.
It does not own the user's model, optimizer meaning, resource scheduler, training loop,
process group, or genome application.

## Installation

From a repository checkout:

```bash
python -m pip install '.[ray]'
```

The current complete path is qualified with Ray 2.56.1, Lightning 2.6.5, PyTorch 2.10.0,
Python 3.11, two CPU members, and one node. Package-only checks also run on Python 3.13.
Broader versions or topologies are not implied by those results.

## End-to-end shape

```python
from pathlib import Path
import tempfile

import lightning.pytorch as pl
import torch
from ray import tune

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback


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
            state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

            # USERSPACE. Restore the selected optimizer history, then apply this member's
            # current Tune config explicitly. CBT does not perform or infer these edits.
            model.optimizer.load_state_dict(state["optimizer_states"][0])
            for group in model.optimizer.param_groups:
                group["lr"] = genome["lr"]
                group["weight_decay"] = genome["weight_decay"]

            # Lightning performs the complete checkpoint restore in trainer.fit(). Put
            # the user's changed optimizer state into this local copy first.
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
    seed=7,
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

There is no CBT trainable wrapper. The scheduler registers the Tune trials with an internal
Ray runtime registry before Ray launches them; `ClanDDPStrategy` discovers the assignment
from the current Tune trial context. The user trainable remains an ordinary Ray function,
which also keeps Ray's normal `Tuner.restore(..., trainable=...)` interface available.

## Genome validity

The package intentionally does not interpret genome keys. That software boundary must not
be confused with the algorithm's scientific boundary.

A varying Clan choice must be applied after the common gradient has been computed. Typical
valid genes are learning rate, weight decay, momentum/betas, or other optimizer-side update
policy. Model architecture, training examples, forward computation, and the loss are not
valid varying Clan genes because they would make members contribute gradients for different
training problems before those gradients are pooled.

The user code shown above is explicit for this reason. CBT must not hide the operation behind
an optimizer schema or application callback.

## Resources and devices

Ray owns trial resources. Request one device per member through the trainable annotation:

```python
cpu_trainable = tune.with_resources(train, {"cpu": 1})
gpu_trainable = tune.with_resources(train, {"cpu": 2, "gpu": 1})
```

Do not normally specify `Trainer(devices=...)`. Lightning defaults to automatic device
selection and Ray exposes only the GPU assigned to the current trial. On the current CPU
path, automatic device count is one. `ClanDDPStrategy` verifies at setup that the Tune trial
has resolved exactly one local Lightning process/device; multiple local devices for a single
member are outside the current topology.

The full population must be runnable concurrently. If `population_size=4` and each trial
requests one GPU, four GPUs must be simultaneously available to the Clan. The current path
does not safely time-multiplex members of the live DDP world.

Ray also owns the number of trials. For a sampled initial population, use
`TuneConfig(num_samples=population_size)`. A fixed `grid_search` can itself produce exactly
the configured population without setting `num_samples`.

## `ClanScheduler`

```python
scheduler = ClanScheduler(
    population_size=4,
    mutations={
        "lr": {
            "standard_deviation": 0.15,
            "geometry": "log",
            "minimum": 1e-5,
            "maximum": 1e-2,
        }
    },
    seed=7,
    join_timeout_s=120.0,
)
```

Configure `metric` and `mode` once, in `tune.TuneConfig`, as with other Ray schedulers. The
scheduler receives those values through Ray's scheduler interface and passes the same
fitness contract to the member-side integration.

Each mutation dictionary has exactly four fields: `standard_deviation`, `geometry`,
`minimum`, and `maximum`. `geometry="linear"` applies an additive Gaussian displacement;
`geometry="log"` applies a multiplicative `exp(N(0, sigma))` displacement. The result is
clamped to the inclusive bounds. Log mutation requires positive values/bounds. Missing,
unknown, or invalid fields fail when the scheduler is constructed rather than during a
later generation.

At each synchronous boundary, the scheduler independently verifies the complete population,
selects the same winner as the workers, snapshots that winner's Tune config, lets Ray retain
the winner checkpoint as the continuation, and gives every next member—including the prior
winner—an independent mutation of the same parent config.

## `ClanDDPStrategy`

```python
trainer = pl.Trainer(strategy=ClanDDPStrategy(), ...)
```

The strategy provides the cross-trial rank/world-size/rendezvous facts Lightning cannot
infer on its own. Lightning/PyTorch still own process-group creation, backend selection,
gradient synchronization, barriers, and teardown. A deliberate ordinary Lightning backend
override remains available through `ClanDDPStrategy(process_group_backend=...)`.

CBT disables per-forward buffer broadcast after setup so member-local persistent buffers are
not overwritten after candidates diverge.

For Lightning-managed dataloaders, training keeps normal DDP partitioning. During
validation and sanity validation, only Lightning's automatically injected distributed
sampler kwargs are changed so every member evaluates the full held-out set. If the user
explicitly supplies a `DistributedSampler`, CBT leaves it untouched; the user is then
responsible for ensuring candidate evaluation remains comparable.

## `ClanTuneReportCallback`

```python
ClanTuneReportCallback()
```

By default the callback reads the same Lightning metric name configured on
`TuneConfig(metric=...)`. If the local Lightning metric has another name:

```python
ClanTuneReportCallback(lightning_metric="validation/loss")
```

Additional callback metrics may be forwarded unchanged:

```python
ClanTuneReportCallback(extra_metrics=["train_loss", "grad_norm"])
```

or renamed for Ray:

```python
ClanTuneReportCallback(
    extra_metrics={"reported_train_loss": "train/loss"},
)
```

The callback gathers one scalar fitness per member through the already-active Lightning
strategy, resolves the common selected member, and has every member participate in
Lightning checkpoint construction/barrier. Only the selected member persists and reports
the Clan continuation checkpoint.

The fitness itself must remain member-local until this exchange. Logging the candidate
fitness with `sync_dist=True` would average/collapse the candidate distinction before CBT
can compare it.

## Checkpoint restoration

Inside an uninterrupted PBT transition, Ray gives each next function invocation the
selected continuation through `tune.get_checkpoint()`. The userspace pattern above preserves
model state, optimizer history, and Lightning loop progress while allowing the new member
config to replace selected optimizer hyperparameters before the framework's full restore.

For an interrupted Tune experiment, use Ray's ordinary experiment restore API with the same
trainable resource annotation:

```python
restored = tune.Tuner.restore(
    experiment_path,
    trainable=tune.with_resources(train, {"gpu": 1}),
    resume_unfinished=True,
    resume_errored=True,
)
results = restored.fit()
```

The framework contract intentionally fails member invocations after a successful
checkpointed Clan transition, shuts down Ray, starts a new Ray runtime, and then exercises
this restore path.

## Current support boundary

Direct complete-path evidence currently covers Python 3.11, Ray 2.56.1, Lightning 2.6.5,
PyTorch 2.10.0, Linux CI, one machine, CPU execution, two concurrent members, repeated
transitions, and interrupted-run restoration. Package-only checks also run on Python 3.13.

Not yet qualified for the complete path: CUDA/NCCL, multi-node execution, actor reuse,
bounded recovery when a participant disappears inside an active distributed collective,
custom/sharded checkpoint plugins, explicitly user-supplied distributed validation-sampler
semantics, ClanFSDP/model-sharded execution, or realistic scientific performance/overhead.

See [`../STATUS.md`](../STATUS.md) for broader repository readiness and
[`qualification/function_api.md`](qualification/function_api.md) for executable evidence.
