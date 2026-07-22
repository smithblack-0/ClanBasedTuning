# ClanBasedTuning

ClanBasedTuning integrates **Clan Based Training** with Ray Tune and Lightning.

Clan Based Training is synchronous Population Based Training over native Tune trials that share a DDP gradient reduction. Each trial keeps its own model trajectory, optimizer state, configuration, checkpoint, and lineage; every trial applies the common reduced gradient using its current optimizer hyperparameters.

Ray remains responsible for PBT selection, checkpoint cloning, configuration mutation, pause, resume, and trial restoration. Lightning remains responsible for the training loop. The package adds a strict PBT subclass, a focused DDP strategy, and small adapters needed to connect those systems safely.

## Current surface

```python
from clan_based_tuning import ClanBase, ClanSpec, OptimizerField

clan = ClanBase(
    ClanSpec(
        population_size=4,
        optimizer_fields=(
            OptimizerField("lr", "lr"),
            OptimizerField("weight_decay", "weight_decay"),
        ),
    )
)

scheduler = clan.scheduler(
    metric="fitness",
    mode="min",
    perturbation_interval=4,
    hyperparam_mutations={
        "lr": tune.loguniform(1e-5, 1e-2),
        "weight_decay": tune.loguniform(1e-6, 1e-1),
    },
)
```

Inside each Tune training function:

```python
strategy = clan.strategy(config)
callback = clan.tune_report_callback(
    metrics={"fitness": "validation_loss"},
    filename="checkpoint",
)

trainer = Trainer(
    strategy=strategy,
    callbacks=[callback],
    **clan.trainer_requirements,
)

with clan.tune_checkpoint_path("checkpoint") as checkpoint_path:
    trainer.fit(model, datamodule=data, ckpt_path=checkpoint_path)
```

Validation/fitness loaders should use `ReplicatedDistributedSampler`, and fitness must be logged with `sync_dist=False`. Training loaders should retain Lightning's normal distributed sharding.

Construct Tune configuration through the facade so the complete population remains resident and actor reuse is disabled:

```python
tuner = tune.Tuner(
    tune.with_resources(train, {"gpu": 1}),
    param_space={},
    tune_config=clan.tune_config(scheduler=scheduler),
    run_config=clan.run_config(
        scheduler=scheduler,
        stop={"training_iteration": 20},
    ),
)
```

## Supported contract

The first build intentionally supports a narrow configuration:

- one native Tune trial per clan member;
- synchronous Ray PBT;
- one Lightning process/device per trial;
- one optimizer and automatic optimization;
- optimizer-only PBT mutations;
- fixed population/world size;
- no actor reuse, time-multiplexing, or independent trial recovery.

`ClanDDPStrategy` supplies required DDP settings automatically and rejects explicit conflicts. The full contract and remaining integration gates are documented in [`docs/engineering/native_trial_build_contract.md`](docs/engineering/native_trial_build_contract.md).

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

The framework-contract suite includes a CPU process-level exploit/restart probe and a native Ray Tune/PBT test. The Ray test is skipped when the optional dependency is unavailable.

## Status

Pre-alpha. The Lightning/DDP execution seam is locally verified. Native Ray PBT execution is defined in the test suite and must pass CI before the build is considered release-ready.
