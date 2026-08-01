# ClanBasedTuning system architecture

Status: active Milestone 3 system design  
Date: 2026-07-31  
Population-resolution clarification: 2026-08-01  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## System result

One live Tune trial represents one Clan member. The complete population forms one
Lightning DDP job for a training round. Lightning DDP supplies the same reduced gradient
to every member, while member-local optimizer state and controlled hyperparameters
produce different updates.

The CBT Tune scheduler is the evolutionary authority. It owns population result
collection, winner verification, mutation, next-member assignments, mutation random
state, lineage, recovery state, and selected-checkpoint redistribution.

Each active `Trial.config` materializes that member's scheduler-assigned genome. The
shared selected checkpoint carries the inherited model, optimizer history, and training
progress. These are separate responsibilities because every receiving member restores
one common continuation and then applies a different child genome.

## Accepted worker lifecycle

The intended user-facing shape remains an ordinary Tune function:

```python
def train(config):
    genome = controlled_subset(config)
    controller = make_cbt_controller(genome=genome)

    model, optimizer = build_training_objects(config)

    checkpoint = tune.get_checkpoint()
    if checkpoint is not None:
        restore_training_state(checkpoint, model, optimizer)

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

This example fixes lifecycle order, not the internal population-resolution mechanism.
`should_save_checkpoint()` means that the runtime has produced one valid local answer
from the complete population before checkpoint reporting. The design does not yet state
how that answer is communicated.

`distributed_checkpoint_boundary()` represents Lightning integration rather than a CBT
training loop. Every DDP rank participates in the required framework boundary; only the
selected member retains a persistent artifact for Tune.

## State authority

The word **genome** means only the Tune configuration fields controlled by CBT, such as
learning rate, optimizer betas, or weight decay.

| State | Authority | Copy or evidence |
| --- | --- | --- |
| Population genomes and next assignments | CBT Tune scheduler | Materialized in target `Trial.config` values |
| Current member genome | Scheduler-assigned `Trial.config` | Controller-owned copied mapping for producer provenance |
| Fitness population | Tune results at the scheduler boundary | Worker-local fitness before reporting |
| Mutation RNG, lineage, and recovery state | CBT Tune scheduler persistence | Optional audit output |
| Model, optimizer history, and training progress | Selected Lightning checkpoint payload | Restored into every next member |
| Genome that produced the selected payload | Winning checkpoint metadata | Verified against the winner's active config |
| Local checkpoint-source answer | Worker controller for the current boundary | Verified by the scheduler-selected winner and sole checkpoint report |

The controller copy is not a second genome authority. It is an independent mapping
snapshot used only to annotate the selected artifact. The design does not require deep
immutability for arbitrary nested objects.

## Population-resolution boundary

Before workers report, exactly one worker must know that it is permitted to retain and
report the checkpoint. This boundary exists because reporting every candidate checkpoint
would perform one expensive save per member.

The accepted behavioral requirements are:

1. every required member reaches the same logical fitness boundary;
2. exactly one comparable fitness value is associated with each stable member;
3. the accepted minimizing or maximizing comparison and stable tie rule are applied;
4. every participating worker reaches a result consistent with the same winner;
5. exactly one worker receives the checkpoint-source answer;
6. a missing, failed, duplicate, or invalid member result prevents advancement; and
7. repeated queries on one worker return the cached answer without repeating the
   population synchronization.

The following are explicitly unresolved:

- whether the existing PyTorch process group or a separate Ray mechanism carries the
  fitness values;
- whether the operation gathers all fitness values or communicates only the final
  decision;
- the callback or object interface;
- stable member-to-rank mapping;
- initialization and teardown;
- timeout and failure release behavior;
- generation separation; and
- implementation module naming.

The inherited `exchange_fitness(local_fitness) -> Sequence[float]` callback from PR #33
is provisional code, not an accepted architectural contract. No new implementation may
copy it merely because it exists on `main`.

## Controller responsibility

The intended thin worker controller owns only:

- a copied current genome mapping for provenance;
- one finite local fitness;
- one cached local checkpoint-source result obtained through the runtime integration;
- the guard that only a resolved selected worker may annotate a checkpoint; and
- producer metadata attachment.

It does not own:

- the communication backend or group lifecycle;
- mutation or child-genome derivation;
- Tune trial configuration;
- model, optimizer, or Lightning state;
- scheduler persistence or recovery;
- generation advancement; or
- a serializable controller continuation.

The concrete controller constructor and runtime-integration signature remain subject to
the current cleanup. Names and docstrings must describe the exact operation rather than
using generic terms such as “exchange” or claiming a qualified collective.

## Producer metadata

The selected worker annotates the checkpoint after Lightning constructs it and before
`tune.report()` publishes it.

The intended metadata is:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

The controller does not write generation identity, Tune trial identity, fitness, child
genomes, mutation state, or lineage because those are scheduler facts.

The ordering is:

```text
construct checkpoint payload
→ attach producer metadata
→ report complete artifact
```

A metadata-write failure prevents publication. This closes the artifact-local crash
window without making checkpoint metadata authoritative over future genomes.

## Scheduler transition

After all members report, the scheduler:

1. verifies one result per required trial;
2. associates each fitness with the reporting trial's active genome;
3. independently selects the winner;
4. verifies that exactly that trial supplied the checkpoint;
5. verifies checkpoint member ID and genome against the winner's active config;
6. derives one child genome per stable target member;
7. persists mutation, lineage, checkpoint reference, and recovery state;
8. installs every target genome;
9. assigns the same selected checkpoint to every target; and
10. releases the complete next population together.

No next-round member may run from a partial scheduler transition. A crash before the
transition commit must recover the last complete generation or fail the experiment.

## Complete generation flow

```text
scheduler assigns one genome per Trial.config
→ every worker restores the same selected checkpoint
→ every worker applies its own assigned genome
→ Lightning DDP trains with shared reduced gradients
→ every worker computes comparable local fitness
→ runtime resolves one checkpoint source from the complete population
→ every DDP rank enters the checkpoint boundary
→ selected worker retains and annotates one checkpoint
→ all workers report; only the selected report includes the checkpoint
→ scheduler verifies winner, metadata, and sole checkpoint source
→ scheduler persists and assigns the complete next transition
→ next population starts together
```

The invariant is:

```text
one common selected training continuation
+ one verified producer-genome record
+ one scheduler-owned next-population transition
→ one coherent next Clan population
```

## Module boundaries

The accepted current organization is:

```text
controller.py
    worker-local fitness and checkpoint-source state
    copied producer-genome snapshot
    winner-only checkpoint annotation

evolution.py
    MutationSpec
    stable winner selection
    future pure child-genome derivation

scheduler_types.py
    dictionary aliases only

scheduler.py
    Tune generation barrier
    mutation state, lineage, persistence, target configs, checkpoint assignment
```

The population-resolution integration module remains unnamed until framework ownership
is chosen. There is no accepted `selection.py` split and no accepted `ray_collective.py`
module.

## Failure boundaries

### Incomplete population

A missing or failed member invalidates the boundary. The implementation must surface or
time out the whole Clan rather than choose from a smaller set.

### Invalid fitness population

Missing, duplicate, non-finite, wrongly ordered, or cross-generation values must fail
before a checkpoint-source answer becomes valid.

### Invalid producer snapshot

The integration must supply the same controlled mapping to the optimizer and controller.
Later mutation of the caller's mapping must not alter the controller-owned copy.

### Missing or multiple checkpoints

The scheduler requires exactly one checkpoint-bearing report from the independently
selected winner.

### Producer disagreement

The checkpoint member ID and genome must match the scheduler-selected winner and that
trial's active controlled config.

### Partial target assignment

No target may start until every target has both its intended child genome and the same
selected checkpoint, backed by a durable scheduler transition.

## Current implementation status

Accepted implementation:

- `MutationSpec` and stable winner selection in `evolution.py`;
- dictionary aliases in `scheduler_types.py`; and
- removal of the old persistent `ClanRound` lifecycle.

Provisional implementation requiring cleanup:

- the current `ClanController` constructor;
- `exchange_fitness` naming and callback shape;
- current `should_save_checkpoint()` docstrings and internal population handling; and
- unit tests that use a fake complete-population exchange.

Not implemented:

- the copied genome snapshot;
- `save_genome()`;
- production population-resolution transport;
- `make_cbt_controller()`;
- the Tune scheduler;
- Lightning checkpoint integration; and
- a real multi-generation workflow.

No provenance or integration implementation should proceed until the provisional
controller seam and governing documentation are cleaned together.
