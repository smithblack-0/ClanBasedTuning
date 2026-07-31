# ClanBasedTuning system architecture

Status: active Milestone 3 system design  
Date: 2026-07-31  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## System result

ClanBasedTuning keeps the ordinary Ray Tune function lifecycle.

One live Tune trial represents one Clan member. Those trial processes form one
Lightning DDP job for a training round. Lightning DDP supplies the same reduced
gradient to every member, while each local optimizer applies that gradient using the
hyperparameters in its current Tune configuration.

The CBT Tune scheduler is the sole evolutionary authority. It owns population result
collection, parent selection, mutation, next-trial configuration, replay state, and
assignment of the selected checkpoint to every trial.

A thin worker-side `ClanController` exists only because CBT must determine the
checkpoint source before calling `tune.report()`. It exchanges fitness across the live
population and returns whether the local worker should attach the checkpoint.

CBT defines no `Trainable` subclass, no independent training loop, no public
`ClanRound`, no controller checkpoint state, and no second population policy.

## The intended imperative Tune function

The ordinary user-facing shape is:

```python

def train(config):
    controller = make_cbt_controller()

    model, optimizer = build_training_objects(config)

    checkpoint = tune.get_checkpoint()
    if checkpoint is not None:
        restore_training_state(checkpoint, model, optimizer)

    apply_optimizer_config(optimizer, config)

    train_one_round(model, optimizer)
    metrics = evaluate(model)

    controller.set_fitness(metrics["fitness"])

    if controller.should_save_checkpoint():
        checkpoint = make_checkpoint(model, optimizer)
        tune.report(metrics, checkpoint=checkpoint)
    else:
        tune.report(metrics)
```

This is the governing usability target. A user should not manually handle rank,
world size, collective-group creation, complete-population gathering, tie breaking,
checkpoint-source selection, mutation, or checkpoint redistribution.

The exact Lightning-qualified form preserves the same visible logic while requiring
all DDP ranks to enter the checkpoint boundary:

```python
controller.set_fitness(metrics["fitness"])
should_save = controller.should_save_checkpoint()

checkpoint = distributed_checkpoint_boundary(
    trainer=trainer,
    persist=should_save,
)

if should_save:
    tune.report(metrics, checkpoint=checkpoint)
else:
    tune.report(metrics)
```

`distributed_checkpoint_boundary()` is an integration responsibility, not a new
training loop. Every Lightning DDP rank participates in the framework checkpoint
operation; only the selected member retains a persistent artifact and passes it to
Tune.

## What the user does not handle

The user train function should not provide or coordinate:

- Clan member rank or population size;
- Ray collective initialization or group names;
- fitness all-gather buffers;
- objective direction or stable tie-breaking logic inside the worker;
- deciding which report carries the checkpoint;
- Tune scheduler pause, stop, or replacement ordering;
- assigning the selected checkpoint to losing trials;
- scheduler mutation state or random streams;
- replay lineage;
- DDP rendezvous, gradient reduction, or winner-aware checkpoint I/O; or
- a CBT-owned round-advancement protocol.

The user retains the ordinary PBT-style responsibilities:

- build the model, optimizer, and data;
- obtain the Tune-assigned checkpoint with `tune.get_checkpoint()`;
- restore training continuation;
- reapply the current trial configuration after optimizer restoration;
- train and evaluate;
- provide one scalar fitness; and
- call `tune.report()` with the optional checkpoint produced at the boundary.

## Governing lifecycle

```text
TUNE STARTS ONE FUNCTION TRIAL PER CLAN MEMBER
│
├── CBT runtime creates the worker controller
├── tune.get_checkpoint() exposes the scheduler-assigned checkpoint, if any
├── restore model, optimizer history, and training progress
└── apply this trial's current Tune configuration to the restored optimizer
│
▼
TRAIN WITH LIGHTNING DDP
│
├── each member processes its own training partition
├── Lightning DDP reduces the gradient across the Clan
└── each local optimizer applies the shared gradient using its own configuration
│
▼
EVALUATE ONE LOCAL FITNESS
│
▼
WORKER CONTROLLER RESOLVES THE CHECKPOINT SOURCE
│
├── set_fitness(local fitness)
├── should_save_checkpoint() all-gathers fitness
├── every member applies the same comparison and tie rule
└── exactly one member receives True
│
▼
LIGHTNING CHECKPOINT BOUNDARY
│
├── every DDP rank participates
├── selected member persists the continuation
└── other members persist nothing
│
▼
REPORT TO TUNE
│
├── every member reports its fitness and round metadata
├── selected member additionally reports the checkpoint
└── losing members report metrics without a checkpoint
│
▼
CBT TUNE SCHEDULER CLOSES THE GENERATION
│
├── verify one complete population
├── independently select the same parent
├── verify exactly that trial supplied the checkpoint
├── mutate each next trial configuration
├── assign the selected checkpoint to every trial
└── replace or resume the complete population together
│
└──────────────────────────────────────────────► TUNE STARTS THE NEXT FUNCTION TRIALS
```

The central invariant is:

```text
one selected training continuation
+ one scheduler-generated configuration per receiving member
→ one next Clan population
```

The common checkpoint supplies training state. The member-specific Tune configuration
supplies the next optimizer hyperparameters. The worker controller supplies neither.

## Why this follows ordinary PBT

Ray PBT already separates inherited state from target-local configuration:

```text
assign source checkpoint to target
→ restore source model and optimizer history
→ apply target's current mutated configuration
→ continue training
```

CBT keeps that shape. Its unusual additions are:

1. the members train concurrently as one Lightning DDP world and intentionally diverge
   after applying the shared gradient; and
2. the checkpoint source must be known in the worker before reporting so losing
   members can avoid expensive persistent checkpoints.

Those additions justify a worker collective controller and Lightning integration. They
do not justify moving evolution or checkpoint loading into that controller.

## Two-round example

Assume members A, B, and C and a minimizing objective.

### Round 4 start

1. The scheduler starts A, B, and C with the checkpoint selected after round 3.
2. Each train function calls `tune.get_checkpoint()` and restores the same model,
   optimizer history, and Lightning progress.
3. The scheduler supplies a different current Tune configuration to each trial.
4. Each train function reapplies its own learning rate, momentum, weight decay, or
   other controlled values after optimizer restoration.
5. Lightning DDP trains the three members with shared reduced gradients and
   member-local optimizer updates.

### Round 4 boundary

6. A, B, and C evaluate to fitness values 0.42, 0.31, and 0.36.
7. Each worker controller stores its local fitness.
8. `should_save_checkpoint()` performs the collective exchange. Every member sees the
   rank-ordered population and identifies B as the source.
9. Every Lightning DDP rank enters checkpointing; only B persists the continuation.
10. A and C report metrics without a checkpoint. B reports metrics with its checkpoint.

### Scheduler transition

11. The scheduler receives all three reports and independently identifies B from the
    reported fitness.
12. It verifies that B is the only checkpoint-bearing report.
13. It assigns B's checkpoint to A, B, and C for the next invocation.
14. It mutates or retains each next trial configuration according to CBT policy.

### Round 5 start

15. Replacement trials retrieve B's checkpoint through `tune.get_checkpoint()`.
16. They restore B's training continuation.
17. They apply their distinct round-5 Tune configurations.
18. The new Lightning DDP population trains and diverges again.

No worker controller survives the transition. No controller state is included in B's
training checkpoint. Scheduler state remains with the Tune scheduler.

## System sequence

```mermaid
sequenceDiagram
    participant S as CBT Tune scheduler
    participant W as Tune worker functions
    participant C as Worker controllers
    participant L as Lightning DDP

    S->>W: Start population with assigned checkpoint and member configs
    W->>W: tune.get_checkpoint()
    W->>L: Restore training continuation
    W->>W: Apply current Tune config to optimizer

    loop Training batches
        W->>L: Local forward/backward
        L-->>W: Shared reduced gradient
        W->>W: Member-local optimizer update
    end

    W->>C: set_fitness(local fitness)
    W->>C: should_save_checkpoint()
    C->>C: All-gather population fitness
    C-->>W: Exactly one local True

    W->>L: All ranks enter checkpoint boundary
    L-->>W: Selected rank retains checkpoint

    W->>S: Report metrics; selected report includes checkpoint
    S->>S: Verify complete population and selected source
    S->>S: Mutate next configurations
    S->>S: Assign selected checkpoint to every trial
    S->>W: Start next population
```

## State ownership

| State | Authority | Persistence |
| --- | --- | --- |
| Model parameters and buffers | Lightning training continuation | Selected Lightning checkpoint |
| Optimizer history | Lightning training continuation | Selected Lightning checkpoint |
| Training progress and precision state | Lightning | Selected Lightning checkpoint |
| Current member optimizer hyperparameters | Tune trial configuration | Tune experiment and scheduler state |
| Mutation random state and replay lineage | CBT Tune scheduler | Tune scheduler persistence |
| Local fitness before report | Worker train function and controller | Tune result after report |
| Collective save decision | Ephemeral worker controller | Not checkpointed |
| Ray collective membership | CBT runtime integration | Recreated for each population |

A training checkpoint must not contain a serialized worker controller, next-member
mutation, or target-local configuration authority.

## Worker `ClanController`

The worker controller owns one small protocol:

```text
unresolved
→ set one finite fitness
→ perform one complete-population exchange
→ cache one local save boolean
```

Its public behavior is:

```python
controller.set_fitness(fitness)
should_save = controller.should_save_checkpoint()
```

`set_fitness()` is local and nonblocking.

The first `should_save_checkpoint()` call is blocking. It invokes the injected
collective, verifies the expected population size, applies objective direction and
stable lower-rank tie breaking, and caches the result. Repeated calls return the cached
boolean and must not re-enter the collective.

The controller does not expose:

- `advance()`;
- current or next configuration access;
- mutation operations;
- state serialization;
- Tune report methods;
- checkpoint methods; or
- a nested `ClanRound`.

The eventual `make_cbt_controller()` factory hides its integration constructor inputs:
member rank, population size, objective direction, and the Ray collective exchange.

## CBT Tune scheduler

The scheduler owns the evolutionary behavior that the earlier controller attempted to
own process-locally.

At each complete generation it:

1. waits for one report from every expected trial;
2. compares the reported fitness under the configured objective;
3. verifies agreement with the single checkpoint-bearing report;
4. selects the checkpoint source;
5. creates the next configuration for every stable member position;
6. assigns the source checkpoint to every next trial;
7. preserves scheduler random state and replay history; and
8. makes the whole next population runnable together.

The scheduler may specialize or reuse Ray's PBT lifecycle mechanisms, but CBT policy
must remain explicit and testable. It must not require a CBT `Trainable` subclass.

The worker and scheduler should use one shared comparison implementation or a directly
cross-checked contract so objective direction and tie behavior cannot diverge.

## Lightning DDP

Lightning's `DDPStrategy` owns Trainer integration, process-group setup, model wrapping,
device placement, barriers, backward synchronization, optimizer lifecycle, and
checkpoint hooks. PyTorch `DistributedDataParallel` is the lower-level gradient
reduction mechanism.

The integration must preserve intentional member divergence:

- retain native DDP initialization;
- retain gradient synchronization;
- disable forward-time persistent-buffer broadcast when it would overwrite local
  member state; and
- do not synchronize parameters or optimizer history after local optimizer updates.

Training data is partitioned normally. Fitness data is equivalent across members, and
fitness remains member-local rather than being reduced into one Lightning metric.

## Checkpoint construction and reporting

The boolean returned by `should_save_checkpoint()` is not a checkpoint request to Ray.
Lightning must construct the selected training continuation before the corresponding
`tune.report()` call.

Every DDP rank participates in the required Lightning checkpoint boundary. A
winner-aware strategy or checkpoint-I/O seam ensures only the selected rank performs
the persistent write.

The selected worker wraps the resulting artifact as a Ray checkpoint and calls:

```python
tune.report(metrics, checkpoint=checkpoint)
```

Other workers call:

```python
tune.report(metrics)
```

Ray's internal function wrapper retains a checkpoint attached to a function report and
makes it available to Tune's save/restore machinery. That wrapper is framework code,
not a CBT abstraction.

## Construction boundary

The intended public factory is:

```python
controller = make_cbt_controller()
```

The factory will read CBT-reserved runtime metadata and initialize or join the fitness
collective. Ordinary users should not pass rank, world size, group name, backend, or
objective direction inside their train function.

The current framework-independent implementation exposes the underlying constructor
only so the worker protocol can be developed and tested before the Ray integration
exists.

## Failure and completion

### Missing collective participant

The fitness exchange requires every active member. Loss of one member invalidates the
complete Clan round. Surviving members must fail or time out rather than choose from a
smaller population.

### Invalid collective result

A wrong-size or non-finite population fails before a save decision is cached.

### Missing or multiple checkpoints

After a complete generation, the scheduler requires exactly one checkpoint-bearing
report and it must belong to the scheduler-selected winner. Zero or multiple
checkpoints invalidate the transition.

### Partial checkpoint assignment

No next trial may begin until the same selected checkpoint has been assigned to every
required member.

### Planned completion

The complete Clan stops only at a common reporting boundary. Independent per-trial
early termination is incompatible with an active shared-gradient population.

## Initial support boundary

The first executable qualification remains narrow:

- one process and one device per Tune trial;
- one fixed, concurrently resident population;
- one Lightning DDP world;
- one Ray fitness collective with the same stable rank mapping;
- equal-length training participation;
- replicated held-out fitness data;
- one supported optimizer mapping for controlled values;
- no competing learning-rate scheduler for those values;
- no elastic world-size change, SyncBatchNorm, FSDP, or model sharding; and
- no CBT or user-defined `Trainable` subclass.

These are evidence limits, not permanent architectural claims.

## Implementation consequences

The accepted earlier `ClanRound` and persistent per-process controller design is
superseded by this flow.

The active code must therefore:

- remove `ClanRound` from the package surface;
- replace controller-owned mutation, population loading, advancement, and persistence
  with the thin worker decision protocol;
- retain `MutationSpec` for the future scheduler;
- implement scheduler evolution and checkpoint assignment separately;
- add a Ray-backed `make_cbt_controller()` factory later; and
- qualify the exact Tune and Lightning seams through framework-contract tests.

## Behavioral-contract traceability

| Behavioral contract | Primary lifecycle evidence |
| --- | --- |
| Common continuation at round start | Scheduler assignment plus Tune checkpoint retrieval and Lightning restore |
| Mutation after inheritance | Restored optimizer history followed by application of current Tune config |
| Shared gradient | Real Lightning DDP gradient observation before optimizer step |
| Controlled divergence | Equal-start, equal-gradient update with distinct Tune configurations |
| Comparable local fitness | Equivalent held-out workload and unreduced member-local metrics |
| Preferred continuation | Worker decision, one reported checkpoint, and next-round restore |
| Partial population cannot advance | Collective failure and scheduler no-assignment evidence |
| Repeated lifecycle | At least two complete function-invocation generations |
| Deterministic next population | Restored scheduler state and reproducible next trial configurations |

## Source-backed framework conclusions

The design continues to rely on these inspected Ray 2.56.1 paths:

- `ray/util/collective/collective.py`: actor-local group initialization and blocking
  `allgather()`;
- `ray/tune/trainable/function_trainable.py`: reported-checkpoint retention, internal
  save returning the latest report, and assigned checkpoint exposure;
- `ray/tune/execution/tune_controller.py`: scheduler result, pause, save, and restore
  ordering; and
- `ray/tune/schedulers/pbt.py`: population mutation and checkpoint reassignment patterns.

The Lightning checkpoint boundary remains based on Lightning 2.6.1
`Trainer.save_checkpoint()`, which constructs the standard Lightning continuation,
delegates persistence to the strategy, and participates in distributed synchronization.

Implementation must protect version-sensitive framework seams with direct contract
tests. Those tests qualify this design; they do not replace the black-box behavioral
contracts.
