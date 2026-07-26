# Milestone 3 manual Clan workflow

Status: proposed integration contract for review  
Qualified versions: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x  
Qualified topology: two or more CPU Tune trials, one Lightning process per trial, Gloo DDP

## Purpose

This milestone proves that the accepted `ClanController` can be manually composed with
native Ray Tune, Lightning, and PyTorch behavior. It deliberately exposes every
Clan-specific component. A later usability frontend may manufacture the same objects,
but it must not replace their responsibilities with a second training system.

## Process-local lifecycle

Every Tune trial executes the same sequence:

```text
construct ClanTuneSession
construct ClanController from session callbacks
construct controller restore and report callbacks
construct ClanLightningEnvironment and ClanDDPStrategy
load Tune's assigned Lightning checkpoint, when present
restore the selected controller parent
controller.advance()
apply this process's next optimizer configuration
form one DDP group with all other live members
train on independently partitioned data
validate on the same held-out workload
publish one completed ClanRound
wait until the complete population exists
controller.is_round_winner()
if winner: serialize one complete local Lightning checkpoint
report metrics, winner identity, and optional checkpoint to Tune
Tune pauses the population and assigns the winner checkpoint to every loser
all next-generation actors reconstruct and repeat
```

The checkpoint contains the selected parent before exploration. Mutation occurs only
after each next-generation process loads that checkpoint.

## Explicit composition

```python
session = ClanTuneSession(config)

controller = ClanController(
    member_id=session.member_id,
    population_size=session.population_size,
    initial_config={"lr": initial_learning_rate},
    mutations=mutations,
    mode="min",
    seed=config["trial_seed"],
    save_member_fitness=session.save_member_fitness,
    load_population=session.load_population,
)

restore = ClanControllerRestore(controller)
report = ClanTuneReportCallback(
    controller,
    metrics={"fitness": "validation_loss"},
    fitness_metric="fitness",
)

environment = ClanLightningEnvironment(session.runtime)
strategy = ClanDDPStrategy(session.runtime, process_group_backend="gloo")

trainer = Trainer(
    accelerator="cpu",
    devices=1,
    num_nodes=1,
    strategy=strategy,
    plugins=[environment],
    callbacks=[restore, report],
    enable_checkpointing=False,
)

with tune_checkpoint_path() as checkpoint_path:
    trainer.fit(model, train_loader, validation_loader, ckpt_path=checkpoint_path)
```

The Tune driver is configured separately:

```python
scheduler = ClanBasedTraining(
    population_size=population_size,
    metric="fitness",
    mode="min",
    perturbation_interval=1,
)

tuner = tune.Tuner(
    tune.with_resources(train, {"cpu": 1}),
    param_space={"trial_seed": tune.grid_search(trial_seeds)},
    run_config=tune.RunConfig(
        stop={"training_iteration": number_of_reports},
        failure_config=tune.FailureConfig(max_failures=0, fail_fast=True),
    ),
    tune_config=tune.TuneConfig(
        scheduler=scheduler,
        max_concurrent_trials=population_size,
        reuse_actors=False,
    ),
)
```

`number_of_reports = number_of_transitions + 1`: Tune does not exploit a terminal
result after its stop condition has already completed the trial.

## Responsibility map

### `ClanTuneSession`

Runs inside one trial process. It resolves stable member identity and DDP topology from
the named Ray rendezvous actor. Its two methods translate controller callbacks into
plain completed-round communication:

- `save_member_fitness(round_)` publishes one local record;
- `load_population(round_index)` waits for one complete population.

It does not choose a winner, checkpoint a model, mutate a configuration, or schedule a
trial.

### `ClanController`

Runs inside every process. Each instance receives the same completed population,
chooses the same sole parent, checkpoints only policy state, and derives the receiving
member's next optimizer configuration after restore.

### `ClanControllerRestore`

Runs in Lightning's callback lifecycle. Lightning includes its controller state in the
winner checkpoint. On restore, this callback advances the receiving controller and
reconciles the live optimizer with `controller.get_config()`.

### `ClanTuneReportCallback`

Runs at the qualifying Lightning validation boundary. It publishes fitness through the
controller, asks whether the local process won, and supplies a checkpoint only for that
winner. It does not coordinate DDP or select the parent itself.

### `save_local_checkpoint`

This is the one version-sensitive Lightning seam. Lightning 2.6 implements
`Trainer.save_checkpoint()` as:

```text
checkpoint_connector.dump_checkpoint()
strategy.save_checkpoint()
strategy.barrier()
```

The public method is intentionally collective. Clan selection has already established
that only one process should save, so the integration reuses Lightning's complete
checkpoint dump and configured strategy write while omitting only that final barrier.
The checkpoint still contains model, optimizer, loop, callback, and other Lightning
state.

### `ClanDDPStrategy`

Owns only Lightning/DDP assumptions that differ when independent Tune trials form one
process group:

- externally supplied rank and world size;
- `init_sync=False` and `broadcast_buffers=False`;
- initial common-model broadcast;
- model and optimizer topology checks;
- automatic sampler topology; and
- allowing a selected nonzero rank to write through `CheckpointIO`.

PyTorch DDP still owns gradient synchronization.

### `ClanBasedTraining`

Runs in the Tune driver and specializes synchronous
`PopulationBasedTraining`. It verifies the winner independently reported by every
process, records the replay path, and reuses PBT's native pause, source-checkpoint
association, target-checkpoint assignment, and resume lifecycle.

It does not run Ray's quantile policy or hyperparameter mutation. Every losing trial is
a target, the controller-selected trial is the only source, and target Tune configs
remain stable so process-local seed and construction inputs are preserved.

## Checkpoint and replay behavior

One checkpoint is created per completed transition, regardless of population size.
The scheduler records:

```text
round index
winner member ID
winner Tune trial ID
winning optimizer configuration
```

Ray experiment persistence serializes this scheduler state. The replay path describes
policy lineage; checkpoint storage remains Ray-owned.

## Data and fitness

Training data uses ordinary DDP partitioning. Validation data must be replicated so
every divergent member evaluates the same held-out workload. Fitness is logged with
`sync_dist=False`; reducing it across DDP ranks would erase the candidate comparison.

## Failure boundary

The supported manual path requires:

- the entire population to be concurrently resident;
- `max_concurrent_trials == population_size`;
- identical resource requests;
- `max_failures=0` and collective run invalidation on member failure;
- `reuse_actors=False`, so every process explicitly reloads the winner checkpoint;
- one Lightning device/process per Tune trial; and
- no Lightning `EarlyStopping` that can terminate one member independently.

A missing member causes result rendezvous timeout or a failed DDP collective. The
integration does not shrink the Clan or reinterpret a partial population as valid.

## Evidence

- `tests/framework_contracts/test_native_trial_lightning_probe.py` isolates the
  Lightning/DDP seam and proves one winner checkpoint, common restore, optimizer-state
  inheritance, post-load local mutation, shared gradients, and divergence.
- `tests/framework_contracts/test_ray_native_pbt_cycle.py` runs repeated real CPU
  transitions through Ray Tune, Lightning, and PyTorch DDP and inspects winner lineage.
- `examples/manual_cpu_clan.py` is the public manual mechanics example using the same
  accepted components.

## Current limitations

This qualification does not establish GPU, multi-node, FSDP, actor reuse, independent
trial recovery, arbitrary optimizer layouts, or the short usability path. The default
optimizer applier supports one optimizer with one parameter group. Those claims remain
outside this milestone's tested support envelope.
