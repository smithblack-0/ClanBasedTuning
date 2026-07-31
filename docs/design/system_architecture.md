# ClanBasedTuning system architecture

Status: active Milestone 3 system design  
Date: 2026-07-31  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## System result

ClanBasedTuning keeps the ordinary Ray Tune function lifecycle.

One live Tune trial represents one Clan member. Those trial processes form one
Lightning DDP job for a training round. Lightning DDP supplies the same reduced
gradient to every member, while each local optimizer applies that gradient using the
controlled hyperparameters in its current Tune configuration.

The CBT Tune scheduler is the sole evolutionary authority. It owns population result
collection, successful-genome identification, mutation, next-trial configuration,
mutation random state, replay lineage, and assignment of the selected checkpoint to
every next trial.

A thin worker-side `ClanController` exists only because the checkpoint source must be
known before the worker calls `tune.report()`. It exchanges fitness across the live
population and returns whether the local worker should attach the checkpoint.

CBT defines no `Trainable` subclass, no independent training loop, no public
`ClanRound`, no checkpointed worker controller, and no second genome authority.

## Intended imperative Tune function

The governing user-facing shape is ordinary PBT plus one collective save decision:

```python
def train(config):
    controller = make_cbt_controller()

    model, optimizer = build_training_objects(config)

    checkpoint = tune.get_checkpoint()
    if checkpoint is not None:
        restore_training_state(checkpoint, model, optimizer)

    # The checkpoint supplies optimizer history. The current Tune config supplies
    # this member's genome for the new round.
    apply_optimizer_config(optimizer, config)

    train_one_round(model, optimizer)
    metrics = evaluate(model)

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

The user should not manually provide rank, world size, collective-group information,
fitness buffers, tie-breaking rules, scheduler mutation state, or checkpoint
redistribution logic.

`distributed_checkpoint_boundary()` represents the Lightning integration rather than a
CBT training loop. Every DDP rank participates in the required framework boundary;
only the selected rank retains a persistent checkpoint and passes it to Tune.

## State authority

The word **genome** means the subset of Tune configuration fields controlled by CBT,
for example learning rate, optimizer betas, or weight decay. Runtime metadata and
uncontrolled model settings are not part of the genome merely because they also appear
in `Trial.config`.

| State | Live authority | Durable or audit copy |
| --- | --- | --- |
| Current member genome | that member's `Trial.config` | Tune experiment state and scheduler lineage |
| Fitness for the current generation | Tune result received by the scheduler | Tune result history |
| Winning parent genome | winner's `Trial.config` at selection time | checkpoint metadata and scheduler lineage |
| Child genomes | scheduler until installed, then each target `Trial.config` | scheduler lineage |
| Mutation RNG and replay history | CBT Tune scheduler | scheduler persistence |
| Model, optimizer history, and training progress | Lightning continuation | selected checkpoint payload |
| Collective save decision | ephemeral worker controller | verified by checkpoint-bearing report |

There are deliberately two different artifacts at the start of the next round:

```text
one common selected training checkpoint
+
one target-local child genome in each Trial.config
```

The checkpoint is the inherited training trajectory. The target trial configuration is
the genome that will act on that trajectory. A shared checkpoint cannot be the live
authority for several different child genomes.

## How the scheduler learns which genome succeeded

Each report reaches the scheduler together with the reporting `Trial` object.
Therefore the scheduler can associate:

```text
reported fitness
+
reporting trial identity
+
reporting trial's current controlled config fields
```

The worker does not need to serialize or repeat its genome in the checkpoint merely so
the scheduler can discover it. The scheduler selects the winner from the complete
fitness population and reads the winning parent genome from that trial's current
configuration.

The worker and scheduler use the same stable comparison rule. The active core provides
one shared selector so minimizing, maximizing, and lower-rank tie behavior cannot drift
between the pre-report collective decision and the scheduler's verification.

## Checkpoint metadata binds the parent genome to the artifact

After the scheduler has the complete population and the single checkpoint-bearing
report, it attaches namespaced provenance metadata to that checkpoint before assigning
it to the next population.

Conceptually:

```python
winner_genome = controlled_subset(winner_trial.config)

checkpoint.update_metadata(
    build_parent_genome_metadata(
        round_index=round_index,
        source_member_id=winner_member_id,
        source_trial_id=winner_trial.trial_id,
        genome=winner_genome,
    )
)
```

The metadata schema is:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "round_index": 7,
        "source_member_id": 2,
        "source_trial_id": "trial_00002",
        "parent_genome": {
            "lr": 0.004,
            "weight_decay": 0.08,
        },
    }
}
```

Ray checkpoint metadata is separate from the Lightning checkpoint payload. Updating it
reads and writes the small metadata mapping through the checkpoint filesystem; it does
not require deserializing model parameters or optimizer tensors.

The metadata is provenance and an integrity check:

> This continuation was produced by this genome in this completed generation.

It is not the live authority for the receiving members' child genomes. Those remain in
the target trials' configurations.

The scheduler should verify that the parent genome recorded in metadata matches the
controlled fields it observed on the winning trial. On recovery or replay, disagreement
between scheduler lineage and checkpoint provenance is a surfaced corruption rather
than an arbitrary choice of authority.

## Governing lifecycle

```text
TUNE STARTS ONE FUNCTION TRIAL PER CLAN MEMBER
│
├── CBT runtime creates the worker controller
├── tune.get_checkpoint() exposes the scheduler-assigned checkpoint, if any
├── restore model, optimizer history, and training progress
└── apply this trial's current genome from config to the restored optimizer
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
REPORT TO TUNE
│
├── every member reports fitness and generation metadata
├── selected member additionally reports the checkpoint
└── losing members report metrics without a checkpoint
│
▼
CBT TUNE SCHEDULER CLOSES THE GENERATION
│
├── verify one complete population
├── independently select the same winner
├── verify exactly that trial supplied the checkpoint
├── read the winner genome from winner Trial.config
├── attach parent-genome provenance to checkpoint metadata
├── derive one child genome per stable target member
├── install each child genome in its target Trial.config
├── assign the same selected checkpoint to every target
└── make the complete next population runnable together
│
└──────────────────────────────────────────────► TUNE STARTS THE NEXT FUNCTIONS
```

The invariant is:

```text
selected training continuation
+ scheduler-selected parent genome provenance
+ target-local child genomes
→ one coherent next Clan population
```

## Two-round example

Assume members A, B, and C and a minimizing objective.

### Round 4 start

1. The scheduler starts A, B, and C with the checkpoint selected after round 3.
2. Every function calls `tune.get_checkpoint()` and restores the same model,
   optimizer history, and Lightning progress.
3. Each trial receives a different round-4 genome in its Tune configuration.
4. Each function reapplies its own controlled optimizer values after restoration.
5. Lightning DDP trains the population with shared reduced gradients and member-local
   optimizer updates.

### Round 4 boundary

6. A, B, and C evaluate to fitness values 0.42, 0.31, and 0.36.
7. Their worker controllers all-gather the values and all identify B as the checkpoint
   source.
8. Every DDP rank enters the checkpoint boundary; only B persists the continuation.
9. A and C report metrics without checkpoints. B reports metrics with its checkpoint.

### Scheduler transition

10. The scheduler receives the three results and their Trial objects.
11. It independently confirms that B is the winner and sole checkpoint source.
12. It reads B's parent genome from the controlled fields in `B.config`.
13. It updates B's checkpoint metadata with the round, source identities, and parent
    genome.
14. It records the transition in scheduler lineage.
15. It derives round-5 child genomes for A, B, and C and installs them in each target
    trial configuration.
16. It assigns B's checkpoint to all three targets.

### Round 5 start

17. Every replacement function retrieves B's checkpoint.
18. Every member restores B's common training continuation.
19. Every member applies its own round-5 genome from Tune configuration.
20. The population trains and diverges again.

No worker controller survives the transition. No child genome is baked into the shared
checkpoint payload.

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

The first `should_save_checkpoint()` call blocks in the injected collective. It
verifies the expected population size, applies the shared winner selector, and caches
the result. Repeated calls return the cached boolean and never re-enter the collective.

The controller owns no genome, mutation rule, Tune config, checkpoint, scheduler state,
or serializable continuation. It exposes no `advance()`, `state_dict()`, or nested round
object.

The eventual `make_cbt_controller()` factory hides member rank, population size,
objective direction, and collective construction from the user function.

## CBT Tune scheduler

At each complete generation, the scheduler:

1. waits for one result from every required trial;
2. associates each fitness with that trial's active genome;
3. selects and verifies the winner;
4. obtains the sole reported checkpoint;
5. attaches parent-genome provenance to checkpoint metadata;
6. records fitness, parent genome, child genomes, checkpoint reference, and mutation
   lineage in scheduler state;
7. derives one child genome per target using the configured mutation rules;
8. installs each child genome through the target trial configuration;
9. assigns the same selected checkpoint to every target; and
10. releases the complete next population together.

The scheduler may reuse Ray PBT lifecycle mechanisms, but it does not use PBT quantile
selection or donor policy unless explicitly adopted by CBT policy. CBT defines no
package-owned `Trainable` subclass.

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

## Checkpoint construction and reporting

The boolean returned by `should_save_checkpoint()` is not a boolean checkpoint request
to Ray. Lightning constructs the continuation before the corresponding report.

Every DDP rank enters the checkpoint boundary. A winner-aware strategy or
checkpoint-I/O seam permits only the selected member to retain a persistent artifact.
The selected worker reports that Ray checkpoint; losing workers report no checkpoint.

The scheduler updates checkpoint metadata only after it has received and verified the
complete population. It must finish metadata attachment and complete assignment before
any target starts the next generation.

## Construction boundary

The intended worker factory remains:

```python
controller = make_cbt_controller()
```

The framework-independent implementation exposes the underlying constructor only while
the Ray runtime factory is developed:

```python
controller = ClanController(
    member_id=rank,
    population_size=world_size,
    mode="min",
    exchange_fitness=all_gather_fitness,
)
```

Genome mutation and checkpoint metadata attachment do not belong in this factory or
worker object. They belong to the scheduler transition.

## Failure boundaries

### Missing collective participant

Loss of one required member invalidates the generation. Surviving members must fail or
time out rather than choose from a smaller population.

### Invalid collective result

A wrong-size or non-finite population fails before a save decision is cached.

### Missing or multiple checkpoints

The scheduler requires exactly one checkpoint-bearing report and it must belong to the
scheduler-selected winner.

### Genome disagreement

The genome used for lineage and checkpoint provenance must equal the controlled subset
of the winner's active `Trial.config`. A mismatch fails the transition.

### Metadata update failure

No target may start from a checkpoint whose required parent-genome provenance could not
be attached and verified.

### Partial target assignment

No next member may begin until every target has both the same selected checkpoint and
its own scheduler-assigned child genome.

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
- equivalent held-out fitness data;
- one supported optimizer mapping for controlled values;
- no competing learning-rate scheduler for those values;
- no elastic world-size change, SyncBatchNorm, FSDP, or model sharding; and
- no CBT or user-defined `Trainable` subclass.

These are evidence limits rather than permanent architectural claims.

## Implementation consequences

The earlier public `ClanRound` and persistent per-process evolutionary controller are
superseded.

The active implementation therefore:

- exposes only a thin worker `ClanController` and `MutationSpec`;
- removes worker-owned mutation, round advancement, population storage, and controller
  checkpoint state;
- shares one winner selector between worker and future scheduler code;
- defines a namespaced parent-genome checkpoint metadata schema;
- leaves Ray-backed `make_cbt_controller()`, the Tune scheduler, and Lightning
  checkpoint integration as subsequent TDD slices; and
- requires framework-contract tests for Tune checkpoint reassignment and checkpoint
  metadata updates against the pinned Ray version.

## Source-backed framework conclusions

The design relies on these inspected Ray 2.56 paths:

- Tune PBT associates performance with `Trial.config`, mutates target configs through
  `trial.set_config(new_config)`, and assigns source checkpoints separately;
- function trials receive assigned checkpoints through `tune.get_checkpoint()` and
  report optional checkpoints through `tune.report()`;
- `Checkpoint.update_metadata()` merges metadata through the checkpoint filesystem;
  its implementation reads and writes the metadata JSON rather than loading checkpoint
  payload tensors; and
- Tune's PBT implementation demonstrates scheduler persistence and replay logging for
  config transitions.

The Lightning checkpoint boundary remains based on Lightning 2.6.x public checkpoint
construction and strategy-owned persistence. Those source conclusions establish a
viable design; direct framework-contract tests must still qualify the exact pinned
versions.
