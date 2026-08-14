# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: a distributed training
method that shares gradients across a population while evolving member-local optimizer
policies online through selection.

## Current function API

The initial complete path uses ordinary Ray Tune function trainables, Lightning, and
PyTorch DDP.

```python
from ray import tune
from clan_based_tuning import (
    ClanDDPStrategy,
    ClanScheduler,
    ClanTuneReportCallback,
    MutationSpec,
)


def train(genome):
    checkpoint = tune.get_checkpoint()

    if checkpoint is not None:
        # USERSPACE. Restore inherited state and use the current genome however
        # your program needs. CBT does not interpret or apply it.
        ...

    trainer = pl.Trainer(
        devices=1,
        strategy=ClanDDPStrategy(),
        callbacks=[ClanTuneReportCallback()],
        ...,
    )
    trainer.fit(...)


population_size = 4
scheduler = ClanScheduler(
    population_size=population_size,
    metric="val_loss",
    mode="min",
    mutations={
        "lr": MutationSpec(
            standard_deviation=0.2,
            geometry="log",
            minimum=1e-5,
            maximum=1e-2,
        )
    },
)

results = tune.Tuner(
    scheduler.wrap(train),
    param_space={"lr": tune.loguniform(1e-4, 1e-3)},
    tune_config=tune.TuneConfig(
        scheduler=scheduler,
        num_samples=population_size,
        max_concurrent_trials=population_size,
    ),
).fit()
```

The important ownership boundary is literal: CBT supplies genomes; user code owns their
meaning and application. The library contains no optimizer application callback, inferred
optimizer schema, or hidden post-load application hook.

[`docs/api.md`](docs/api.md) contains the complete Lightning checkpoint-restore pattern,
including an explicit userspace example that preserves inherited optimizer history and
Lightning training progress while applying a newly assigned genome.

## What CBT owns

The initial integration adds only the Clan-specific pieces around framework-native
training:

- `ClanScheduler` uses Ray's synchronous PBT lifecycle but selects one parent continuation
  for the whole Clan and independently mutates that parent genome for every next member;
- `ClanDDPStrategy` connects one externally launched Tune trial per Clan member into the
  Lightning/PyTorch DDP world without selecting another backend or process group;
- `ClanTuneReportCallback` compares member-local fitness over that existing distributed
  context and persists/reports only the selected CBT continuation; and
- `ClanController` and `MutationSpec` provide the framework-independent selection and
  mutation primitives behind that integration.

All ranks may transiently construct Lightning checkpoint state because the checkpoint
boundary is collective. Only the winner persists the CBT continuation, so permanent CBT
checkpoint storage scales with rounds rather than population size times rounds.

## Qualified path

The complete function path is directly exercised over two successive generations with two
concurrent members on one CPU node using Ray 2.56.1, Lightning 2.6.5, PyTorch 2.10.0, and
Python 3.11. The contract verifies shared gradients, winner selection, one persistent
continuation, Ray checkpoint transfer, userspace genome use, inherited model/optimizer
history/Lightning progress, and independent next-gen mutations for every member.

The complete path is not yet qualified for CUDA/NCCL, multi-node execution, actor reuse,
active-collective failure recovery, arbitrary validation-sampler arrangements, or
ClanFSDP/model-sharded execution. See [`STATUS.md`](STATUS.md) and
[`docs/qualification/function_api.md`](docs/qualification/function_api.md) for the precise
support boundary.

## Installation and development

The Ray/Lightning integration is optional:

```bash
python -m pip install -e '.[ray]'
```

Development validation:

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Documentation starts at [`docs/README.md`](docs/README.md). The governing project contract
is [`docs/product_roadmap.md`](docs/product_roadmap.md).
