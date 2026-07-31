# ClanBasedTuning system architecture

Status: active Milestone 3 system design  
Date: 2026-07-31  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## System result

ClanBasedTuning keeps the ordinary Ray Tune function lifecycle.

One live Tune trial represents one Clan member. Those trial processes form one
Lightning DDP job for a training round. Lightning DDP supplies the same reduced
gradient to every member, while each local optimizer applies that gradient using the
controlled hyperparameters assigned to that member.

The CBT Tune scheduler is the evolutionary authority. It owns population result
collection, winner verification, mutation, next-member assignments, mutation random
state, replay lineage, recovery state, and selected-checkpoint redistribution.

The active genome for one worker is the controlled subset of that worker's
`Trial.config`. That configuration is the scheduler's materialized assignment for the
round, not an independent policy owner.

A thin worker-side `ClanController` exists for two closely related worker-boundary
responsibilities:

1. exchange fitness across the live population and decide whether this worker is the
   sole checkpoint source; and
2. if this worker is selected, attach the exact genome snapshot used by this worker to
   the completed checkpoint before it is reported to Tune.

The controller does not select or manufacture future genomes. It does not own mutation,
lineage, scheduler recovery, or checkpoint redistribution.

CBT defines no package-owned `Trainable` subclass, no independent training loop, no
public `ClanRound`, and no second checkpoint format.

## Intended imperative Tune function

The governing user-facing shape is ordinary PBT plus one collective save decision and
one winner-side provenance write:

```python
def train(config):
    genome = controlled_subset(config)
    controller = make_cbt_controller(genome=genome)

    model, optimizer = build_training_objects(config)

    checkpoint = tune.get_checkpoint()
    if checkpoint is not None:
        restore_training_state(checkpoint, model, optimizer)

    # The checkpoint supplies optimizer history. The current Tune config supplies
    # this member's scheduler-assigned genome for the new round.
    apply_optimizer_config(optimizer, genome)

    train_one_round(model, optimizer)
    metrics = evaluate(model)

    controller.set_fitness(metrics["fitness"])
    should_save = controller.should_save_checkpoint()

    checkpoint = distributed_checkpoint_boundary(
        trainer=trainer,
        persist=should_save,
    )

    if should_save:
        checkpoint = controller.save_genome(checkpoint)
        tune.report(metrics, checkpoint=checkpoint)
    else:
        tune.report(metrics)
```

`distributed_checkpoint_boundary()` represents the Lightning integration rather than a
CBT training loop. Every DDP rank participates in the required framework boundary;
only the selected rank retains a persistent checkpoint and passes it to Tune.

The user should not manually provide rank, world size, collective-group information,
fitness buffers, tie-breaking rules, scheduler mutation state, or checkpoint
redistribution logic. The user or integration layer does provide the controlled genome
snapshot because it is derived from the same `config` that is applied to the optimizer.

## State authority

The word **genome** means the subset of Tune configuration fields controlled by CBT,
for example learning rate, optimizer betas, or weight decay. Runtime metadata and
uncontrolled model settings are not part of the genome merely because they also appear
in `Trial.config`.

| State | Authority | Copies or evidence |
| --- | --- | --- |
| Population genomes and next-generation assignments | CBT Tune scheduler | Materialized in each target `Trial.config` |
| Current member genome during one round | That member's scheduler-assigned `Trial.config` | Immutable controller snapshot for provenance |
| Fitness for the current generation | Tune results collected by the scheduler | Worker-local value before reporting |
| Mutation RNG, replay lineage, and recovery state | CBT Tune scheduler persistence | Optional audit logs |
| Model, optimizer history, and training progress | Selected Lightning checkpoint payload | Restored into every next member |
| Genome that produced the selected payload | Winning checkpoint metadata | Verified against the winner's `Trial.config` |
| Collective checkpoint-source decision | Ephemeral worker controller | Verified by the checkpoint-bearing report |

The checkpoint genome metadata is provenance, not a second evolutionary authority. It
answers:

> Which assigned genome actually produced this training continuation?

The scheduler answers:

> Which child genomes should run next, and how should the experiment recover and replay
> that decision?

## Controller genome snapshot

`make_cbt_controller(genome=genome)` copies the supplied mapping at construction. The
snapshot represents the exact controlled values intended for this worker's current
round.

The controller:

- does not mutate the snapshot;
- does not derive a child genome;
- does not expose it as another live configuration authority;
- does not restore it into the optimizer; and
- does not persist it unless this worker is selected to save.

The snapshot exists so the winner can bind its completed artifact to the values it
actually used without waiting for a later scheduler-side metadata mutation.

## Winning checkpoint metadata

The selected worker calls `controller.save_genome(checkpoint)` after Lightning has
constructed the checkpoint and before `tune.report()` publishes it.

The minimal metadata schema is:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": 2,
        "genome": {
            "lr": 0.004,
            "weight_decay": 0.08,
        },
    }
}
```

The controller intentionally does not write:

- a round or generation index;
- a Tune trial ID;
- fitness;
- comparison mode;
- child genomes;
- mutation random state; or
- scheduler lineage.

The controller does not reliably own those values, and they are not required to prove
which member genome produced the checkpoint. Generation identity and trial lifecycle
remain scheduler state.

`save_genome(checkpoint)` requires a resolved winning decision. Calling it before
`should_save_checkpoint()` resolves, or on a losing worker, is an error. It merges the
namespaced mapping through the checkpoint metadata interface and returns the same
checkpoint reference.

Ray checkpoint metadata is separate from the Lightning checkpoint payload. The direct
framework contract must prove that adding the mapping does not deserialize or alter
model parameters, optimizer tensors, or the checkpoint file payload.

## Exact generation transition

```text
TUNE STARTS ONE FUNCTION TRIAL PER CLAN MEMBER
│
├── scheduler-assigned Trial.config contains this member's genome
├── worker copies that genome into its controller
├── tune.get_checkpoint() exposes the common selected checkpoint, if any
├── restore model, optimizer history, and training progress
└── apply this member's current genome from config
│
▼
TRAIN WITH LIGHTNING DDP
│
├── each member processes its own training partition
├── Lightning DDP reduces gradients across the Clan
└── each local optimizer applies the shared gradient with its own genome
│
▼
EVALUATE ONE LOCAL FITNESS
│
▼
WORKER CONTROLLER RESOLVES THE CHECKPOINT SOURCE
│
├── set_fitness(local fitness)
├── should_save_checkpoint() all-gathers fitness
├── every member applies the shared comparison rule
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
WINNER BINDS ITS GENOME TO THE ARTIFACT
│
├── controller.save_genome(checkpoint)
├── metadata contains only schema version, member ID, and genome
└── failure prevents the checkpoint from being reported
│
▼
REPORT TO TUNE
│
├── every member reports fitness
├── selected member additionally reports the annotated checkpoint
└── old-generation workers do not advance
│
▼
CBT TUNE SCHEDULER CLOSES THE GENERATION
│
├── wait for one result from every required trial
├── independently select the same winner
├── verify exactly that trial supplied the checkpoint
├── read the checkpoint genome metadata
├── verify member ID and genome against the winner's Trial.config
├── derive one child genome per stable target member
├── persist mutation, lineage, and recovery state
├── install each child genome in its target Trial.config
├── assign the same selected checkpoint to every target
└── release the complete next population together
│
└──────────────────────────────────────────────► TUNE STARTS THE NEXT FUNCTIONS
```

The invariant is:

```text
one selected training continuation
+ one verified producer-genome record
+ one scheduler-owned next-population transition
→ one coherent next Clan population
```

## Why the winner writes metadata before reporting

A scheduler-side metadata write after receiving the checkpoint creates an avoidable
half-complete artifact state:

```text
checkpoint payload reported
→ scheduler later attempts to attach producer genome
```

If the scheduler crashes between those steps, Tune may hold a valid training payload
without the provenance required to verify the transition.

The winner-side ordering is stronger:

```text
construct payload
→ attach producer genome
→ report one complete artifact
```

A metadata-write failure therefore prevents publication of an incomplete winner
artifact.

This does not make the controller authoritative over genomes. The controller merely
records the immutable scheduler assignment that it was given for this round.

## Scheduler transition atomicity

Winner-side metadata attachment closes the artifact-local atomicity gap, but the
scheduler transition still has its own commit boundary.

The scheduler must not release any next-round trial until all of the following are
true:

1. the complete generation has reported;
2. the winner and sole checkpoint source agree;
3. checkpoint metadata matches the winner's member ID and active genome;
4. all child genomes have been derived;
5. mutation RNG and lineage state needed for recovery have been persisted;
6. every target `Trial.config` contains its assigned child genome; and
7. every target has been assigned the same selected checkpoint.

A crash before that transition is durably committed must recover the last completed
scheduler generation or fail the experiment. It must not release a partially assigned
population.

The exact Ray persistence and recovery seam remains version-sensitive and requires a
direct framework-contract test against the pinned Ray version.

## Two-round example

Assume members A, B, and C and a minimizing objective.

### Round 4 start

1. The scheduler assigns one common checkpoint and three child genomes through the
   three trial configurations.
2. Each function copies its controlled genome into its controller.
3. Every function restores the common model, optimizer history, and Lightning progress.
4. Every function reapplies its own assigned genome after restoration.
5. Lightning DDP trains the population with shared reduced gradients and member-local
   optimizer updates.

### Round 4 boundary

6. A, B, and C evaluate to fitness values 0.42, 0.31, and 0.36.
7. Their worker controllers all-gather the values and all identify B as the checkpoint
   source.
8. Every DDP rank enters the checkpoint boundary; only B persists the continuation.
9. B writes `{member_id: B, genome: B.config controlled subset}` into checkpoint
   metadata.
10. A and C report metrics without checkpoints. B reports metrics with its completed,
    annotated checkpoint.

### Scheduler transition

11. The scheduler independently confirms that B is the winner and sole checkpoint
    source.
12. It reads B's checkpoint metadata and verifies the member ID and genome against
    B's active trial configuration.
13. It derives round-5 child genomes, advances its mutation state and lineage, and
    persists that scheduler transition.
14. It installs one child genome in each target trial configuration.
15. It assigns B's checkpoint to all three targets and releases the complete population.

### Round 5 start

16. Every replacement function retrieves B's checkpoint.
17. Every member restores B's common training continuation.
18. Every member applies its own round-5 genome from Tune configuration.
19. The population trains and diverges again.

No worker controller survives the transition. No child genome is baked into the shared
checkpoint payload or metadata.

## Worker `ClanController`

The worker controller owns one small protocol:

```text
constructed with immutable current genome snapshot
→ set one finite fitness
→ perform one complete-population exchange
→ cache one local save boolean
→ winner may save its genome onto the checkpoint
```

Its intended public behavior is:

```python
controller.set_fitness(fitness)
should_save = controller.should_save_checkpoint()

if should_save:
    checkpoint = controller.save_genome(checkpoint)
```

The controller owns no mutation rule, child genome, scheduler state, replay history, or
serializable continuation. It exposes no `advance()`, `state_dict()`, or nested round
object.

## CBT Tune scheduler

At each complete generation, the scheduler:

1. waits for one result from every required trial;
2. associates each fitness with that trial's active genome;
3. selects and verifies the winner;
4. obtains the sole reported checkpoint;
5. verifies its producer metadata against the winner's active assignment;
6. derives one child genome per target using the configured mutation rules;
7. records fitness, parent genome, child genomes, checkpoint reference, mutation state,
   and lineage in scheduler persistence;
8. installs each child genome through the target trial configuration;
9. assigns the same selected checkpoint to every target; and
10. releases the complete next population together.

The scheduler may reuse Ray PBT lifecycle mechanisms, but it does not use PBT quantile
selection or donor policy unless explicitly adopted by CBT policy.

## Lightning DDP

Lightning owns the training loop, process-group behavior, gradient reduction,
optimizer lifecycle, checkpoint construction, and distributed barriers.

The CBT integration must preserve intended member divergence:

- retain native DDP initial synchronization;
- retain gradient synchronization;
- disable forward-time persistent-buffer broadcast where it would overwrite local
  member state; and
- do not synchronize parameters or optimizer history after local optimizer updates.

Training data is partitioned normally. Fitness data is equivalent across members, and
fitness remains member-local rather than being reduced into one Lightning metric.

## Module boundaries

The package organization must communicate the same ownership model as the runtime:

```text
controller.py
    thin worker collective decision
    immutable current-genome snapshot
    winner-only save_genome(checkpoint)

selection.py
    shared deterministic winner comparison

evolution.py or scheduler_types.py
    MutationSpec and pure child-genome derivation

scheduler.py
    Tune generation barrier, mutation state, lineage, persistence,
    target config installation, and checkpoint assignment

ray_collective.py
    make_cbt_controller() and ordered fitness exchange
```

`MutationSpec`, scheduler metadata construction, and checkpoint-transition effects do
not belong in `controller_types.py`. A controller support module may contain only types
that genuinely support the thin controller.

## Failure boundaries

### Missing collective participant

Loss of one required member invalidates the generation. Surviving members must fail or
time out rather than choose from a smaller population.

### Invalid collective result

A wrong-size or non-finite population fails before a save decision is cached.

### Invalid genome snapshot

The controller receives the same controlled mapping that the training function applies
to the optimizer. The integration must not silently derive two different snapshots.
Serialization failures surface when the winner attempts to write metadata.

### Losing or unresolved metadata write

`save_genome()` is valid only after the controller has resolved that this member is the
winner. Calling it earlier or on a loser fails.

### Missing or multiple checkpoints

The scheduler requires exactly one checkpoint-bearing report and it must belong to the
scheduler-selected winner.

### Genome disagreement

The member ID and genome recorded in checkpoint metadata must equal the selected
winner's active `Trial.config`. A mismatch invalidates the transition.

### Metadata update failure

The winner must not report a checkpoint whose genome metadata could not be attached.

### Partial target assignment

No next member may begin until every target has both the same selected checkpoint and
its own scheduler-assigned child genome, with the corresponding scheduler transition
persisted.

## Initial support boundary

The first executable qualification remains narrow:

- one process and one device per Tune trial;
- one fixed, concurrently resident population;
- one Lightning DDP world;
- one Ray fitness collective with the same stable rank mapping;
- equal-length training participation;
- equivalent held-out fitness data;
- one supported optimizer mapping for controlled values;
- no competing learning-rate scheduler for those values;
- no elastic world-size change, SyncBatchNorm, FSDP, or model sharding; and
- no CBT or user-defined `Trainable` subclass.

These are evidence limits rather than permanent architectural claims.

## Implementation consequences

The active implementation must next be corrected to match this design:

- extend `ClanController` with an immutable genome snapshot;
- add winner-only `save_genome(checkpoint)`;
- replace parent-provenance metadata containing round and trial identity with the
  minimal `{schema_version, member_id, genome}` schema;
- move mutation and scheduler concerns out of `controller_types.py`;
- preserve the thin controller's existing fitness and save-decision behavior;
- qualify metadata attachment against Ray 2.56 before implementing the scheduler; and
- then implement the Ray-backed factory, Tune scheduler, and Lightning checkpoint path
  as separate TDD slices.
