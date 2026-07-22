# Native Tune-trial build contract

Status: authoritative implementation contract

Date: 2026-07-22

## Product statement

Clan Based Training is synchronous Population Based Training in which native Ray
Tune trials retain ordinary trial identity, configuration, checkpoint, pause,
resume, and exploit behavior while joining one PyTorch DDP process group and
consuming a shared reduced gradient.

The integration composes Ray and Lightning at their native extension points. It
does not introduce a replacement Trainer, Tune frontend, model wrapper, gradient
reducer, or optimizer configuration language.

## Public composition

There are two real construction points, and the API exposes both directly.

On the Ray driver:

```python
scheduler = ClanBasedTraining(population_size=4, **ordinary_pbt_arguments)
```

Inside each Tune training function:

```python
clan = make_clan_lightning_plugins(config, metrics={"fitness": "val_loss"})

trainer = Trainer(
    strategy=clan.strategy,
    plugins=[clan.environment],
    callbacks=[clan.report_callback],
    devices=1,
    num_nodes=1,
)
prepare_clan_trainer(trainer)

with tune_checkpoint_path() as checkpoint_path:
    trainer.fit(model, ckpt_path=checkpoint_path)
```

`make_clan_lightning_plugins` returns the actual units inserted into Lightning.
It does not return another factory. The model remains a normal
`LightningModule` passed explicitly to `Trainer.fit`; Lightning applies the DDP
transform during its ordinary strategy lifecycle.

## Ownership

### Ray `PopulationBasedTraining`

Ray remains authoritative for trial identity, scoring, mutation, checkpoint
selection and cloning, pause, resume, and scheduler persistence.

### `ClanBasedTraining`

The scheduler subclass adds only clan constraints and rendezvous lifecycle:

- synchronous PBT is mandatory;
- result buffering is disabled;
- the expected population is fixed;
- all members request one identical resource bundle;
- independent member retry is rejected;
- the complete stable trial-ID set is published to rendezvous.

Ray's synchronous PBT path pauses every population member at a perturbation
boundary, including members that are not exploited, before choosing paused
trials to run again. CBT relies on that native lifecycle so all actors leave the
old process group and rendezvous for the next window together.

It accepts Ray's ordinary PBT configuration language. It does not interpret
optimizer fields, construct `TuneConfig` or `RunConfig`, select stop rules, or
ban unrelated search and training features preemptively.

The one reserved trial-config key stores the rendezvous identity. Built-in
mutations may not target it, and the scheduler verifies that `custom_explore_fn`
did not alter it after native Ray exploration.

### `ClanLightningEnvironment`

This literal Lightning `ClusterEnvironment` plugin presents the externally
created rank, world size, master address, and master port. It prevents Lightning
from launching child processes or replacing the cross-trial rank assignment.

The rendezvous actor assigns ranks by sorting the complete native Tune trial-ID
set. Actor tokens identify process-group incarnations and are not durable user
configuration.

### `ClanDDPStrategy`

The strategy owns only framework behavior that ordinary identical-replica DDP
cannot express:

- force `init_sync=False` and `broadcast_buffers=False`;
- verify model, buffer, optimizer-class, and parameter-group topology;
- synchronize the initial model once for a fresh population;
- call an injected optimizer strategy after construction and restore;
- allow every native Tune trial/rank to write its own checkpoint.

It calls `DDPStrategy.configure_ddp()` for the actual wrapper. PyTorch
`DistributedDataParallel` owns gradient bucketing, communication scheduling, and
all-reduce. ClanBasedTuning contains no gradient shuffling or reduction
implementation.

The strategy does not own trial ranking, mutation, checkpoint selection,
optimizer semantics, the training loop, callbacks, schedulers, or manual versus
automatic optimization policy.

### `prepare_clan_trainer`

This function validates the already assembled Trainer and returns it unchanged.
It checks the strategy/environment/callback pairing, one-process topology, and
absence of member-local `EarlyStopping`. It does not inject components or act as
an approval system for ordinary Lightning features.

## Optimizer authority and restore order

Ray PBT creates two legitimate authorities:

- the source checkpoint owns model parameters, optimizer moments/state, and
  training progress;
- the current target-trial config owns the selected hyperparameters.

Lightning restores the source optimizer state first. The strategy then invokes:

```python
apply_optimizer_strategy(trainer.optimizers, current_trial_config)
```

The built-in function supports one optimizer with one parameter group and copies
same-named top-level config values into that group. It ignores unrelated config
keys and never changes `params`.

This built-in limitation is not a restriction of the core strategy. A caller can
inject a function that selects multiple optimizers or groups, maps aliases,
updates tuple elements, or transforms values. Optimizer interpretation is not
serialized into clan metadata and is not duplicated in the scheduler.

The same function runs after initial optimizer construction. This makes the
default layout limitation fail before the first exploit and is idempotent for
models that already construct their optimizer from `config`.

## Checkpoint lifecycle

Ray remains checkpoint authority.

1. Ray's Lightning callback asks the local Trainer to construct a checkpoint and
   reports it to Tune.
2. The strategy removes Lightning's global-rank-zero save gate because every DDP
   rank is a different native Tune trial with a different path.
3. PBT selects and clones the reported source checkpoint.
4. `tune_checkpoint_path()` materializes the current Ray checkpoint for the
   lifetime of `Trainer.fit`.
5. Lightning restores model, optimizer, progress, and callback state.
6. The optimizer strategy reapplies the target trial's current configuration.

If Ray supplied a checkpoint and user code fails to pass it to `Trainer.fit`,
the strategy crashes instead of silently restarting that member.

## DDP and data invariants

Disabling `init_sync` prevents DDP's normal rank-zero parameter broadcast from
erasing restored population differences. The strategy replaces the associated
schema check explicitly and broadcasts parameters and buffers only when every
member agrees that the population is fresh.

Disabling `broadcast_buffers` prevents forward-time rank-zero buffer ownership.
`SyncBatchNorm` remains incompatible because it introduces another forward-state
collective across deliberately divergent members.

Training data retains Lightning's normal distributed sharding. Fitness loaders
should use `replicated_sampler(dataset)`, which returns PyTorch's built-in
`DistributedSampler(num_replicas=1, rank=0)`. Fitness must be logged with
`sync_dist=False` so PBT receives member-local values.

## Initial scope limits

The first implementation requires:

- the complete population resident concurrently;
- synchronous progress boundaries;
- one Lightning process/device and one Ray resource bundle per trial;
- fixed world size during a window;
- compatible model and optimizer topology;
- no independent member failure recovery;
- no member-local termination while peers remain in collectives;
- explicit Ray checkpoint materialization on restore.

Multi-node membership, actor reuse, time multiplexing, FSDP/DeepSpeed
composition, and independent failure recovery are not implemented. Multiple
optimizers, multiple parameter groups, manual optimization, Lightning schedulers,
ordinary checkpoint callbacks, and DDP communication hooks are not rejected by
the core integration; their correctness remains the user's explicit composition
responsibility, with optimizer layouts handled by the injected strategy.

## Verification gates

The CPU process contract verifies common reduced gradients with divergent
optimizer application, member-local checkpoint creation, exploit-style source
restoration, target-config reconciliation, and process-group reformation.

The Ray contract verifies a native Tune population, rendezvous, synchronous PBT
exploit, checkpoint delivery, and restoration. Full `Tuner.restore()` coverage
remains a separate integration gate.
