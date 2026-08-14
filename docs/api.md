# Public API

Status: qualified pre-release function path

## Mental model

One Ray Tune trial is one Clan member and one Lightning process/device. Members form one
Lightning/PyTorch DDP world: training data is partitioned and gradients are reduced normally,
while each member retains its own optimizer state and current Tune config. At a qualifying
validation boundary CBT compares member-local fitness, selects one parent checkpoint, and
constructs one independently mutated child config for every next member.

CBT owns the Clan population transition and the small framework seams needed to connect
independent Tune trials. It does not own the user's model, optimizer meaning/application,
training loop, process-group backend, Ray resources, or experiment storage.

## Installation and compatibility

Install the package normally:

```bash
python -m pip install .
```

Ray Tune, Lightning, and PyTorch are runtime dependencies because the public package is their
integration. Dependency metadata deliberately does not pin one Ray minor release. The current
minimums are Ray 2.56, Lightning 2.6, and PyTorch 2.10, all bounded below the next major
version. Direct current qualification is Ray 2.57.0, Lightning 2.6.5, PyTorch 2.10.0+cpu,
Python 3.11.15, Linux, one CPU node, and two members. The broader dependency range indicates
installability, not automatic qualification.

## End-to-end shape

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
        # USERSPACE: Lightning restored optimizer history before this hook.
        for group in self.optimizer.param_groups:
            group["lr"] = self.genome["lr"]
            group["weight_decay"] = self.genome["weight_decay"]

    def training_step(self, batch, batch_index):
        ...

    def validation_step(self, batch, batch_index):
        loss = ...
        self.log("val_loss", loss)  # candidate fitness remains member-local

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

There is no CBT trainable wrapper and no CBT application callback. `tune.get_checkpoint()`
contains the selected training continuation; the function argument contains the receiving
member's current child genome. Lightning restores model/optimizer/progress through its normal
`ckpt_path` mechanism. User code then applies desired config values to the restored optimizer
in its own Lightning lifecycle.

## Genome validity

CBT deliberately does not interpret genome keys, but Clan Tuning requires varying choices to
be applied after the shared gradient has been computed. Learning rate, weight decay,
momentum/betas, and other optimizer-side update policy are the intended genes. Architecture,
training examples, forward computation, or loss variation would make members contribute
gradients for different problems and is not valid Clan Tuning.

Candidate fitness must remain member-local until population comparison. Logging the selection
metric with `sync_dist=True` would collapse the signal CBT needs.

## Resources and topology

Ray owns trial resources. Request one device per member through `tune.with_resources`.
`ClanDDPStrategy` expects the device visible to one Tune trial to resolve to one Lightning
process/device; users normally do not repeat `Trainer(devices=1)`.

Each independently launched Tune member is presented to Lightning as one logical one-process
node: local rank zero, with logical node rank equal to the external Clan/global rank. This is
an adapter representation that preserves Lightning's rank model; it is not physical-node
identity. Multi-node qualification must revisit the representation if physical topology
becomes relevant.

The complete Clan must fit concurrently. The scheduler waits until Tune has created the
configured trial population before launching members and will not resume an early-paused
member while another member is still completing the current generation boundary. The runtime
also has a bounded pre-DDP rendezvous. CBT does not own a separate cross-trial gang scheduler.

## `ClanScheduler`

```python
ClanScheduler(
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

Configure `metric` and `mode` once through `TuneConfig`, like other Tune schedulers. Mutation
rules have exactly four fields: Gaussian `standard_deviation`, `geometry` (`linear` additive
or `log` multiplicative), and inclusive `minimum`/`maximum` bounds.

At one completed boundary, the scheduler verifies one result from every stable member at the
same Tune iteration, independently selects the same winner reported by workers, captures the
selected member's Tune checkpoint, snapshots its config, creates one sibling mutation for
every member in stable member-ID order, and assigns the selected checkpoint plus each child
config before Tune resumes the population.

The scheduler owns this small synchronous algorithm directly rather than subclassing Ray's
private PBT implementation. Remaining Tune checkpoint/config transfer details are isolated in
`ray_compat.py`.

## `ClanDDPStrategy`

```python
trainer = pl.Trainer(strategy=ClanDDPStrategy(), ...)
```

The strategy supplies cross-trial topology facts Lightning cannot infer. Lightning and
PyTorch still own backend selection, process-group initialization, DDP setup, gradient
collectives, barriers, and teardown. CBT disables per-forward DDP buffer broadcast so one
candidate's post-update persistent buffers do not overwrite another candidate.

Training keeps ordinary DDP partitioning. For Lightning-managed validation and sanity
validation, the strategy supplies one-replica sampler kwargs on every member so each candidate
sees the complete held-out dataset. Explicit user `DistributedSampler` objects remain
user-owned and outside this automatic behavior.

## `ClanTuneReportCallback`

```python
ClanTuneReportCallback()
```

By default the callback reads the same Lightning metric named in `TuneConfig(metric=...)`.
`lightning_metric=` may name a different local Lightning metric, and `extra_metrics=` may
forward additional callback metrics.

The callback gathers one scalar fitness per member through the already-active Lightning DDP
strategy and uses the shared pure selection function. Every rank enters Lightning checkpoint
construction/barrier, while only the selected rank persists and reports the Tune checkpoint.
The callback contains no optimizer/genome application behavior.

## Interrupted experiment restore

Use Ray's ordinary restore API with the same trainable resource annotation:

```python
restored = tune.Tuner.restore(
    experiment_path,
    trainable=tune.with_resources(train, {"gpu": 1}),
    resume_unfinished=True,
    resume_errored=True,
)
results = restored.fit()
```

Scheduler state preserves member assignment, mutation RNG, and runtime identity while live
actor handles are excluded from serialization. The qualified CPU contract reconstructs those
actors in a fresh Ray runtime and continues both errored members.

## Current support boundary

The corrected two-member single-node CPU path is directly qualified on Ray 2.57.0,
Lightning 2.6.5, PyTorch 2.10.0+cpu, Python 3.11.15, and Linux. Package/non-Ray validation also
passes on Python 3.13. CUDA/NCCL, physical multi-node execution, active-collective failure
recovery, custom/sharded checkpoints, arbitrary distributed validation samplers,
model-sharded Clan execution, and realistic performance remain separate support work.
