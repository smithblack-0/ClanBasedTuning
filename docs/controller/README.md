# Worker-side Clan controller

Status: active worker checkpoint-decision and producer-provenance contract

## Purpose

`ClanController` hides the unusual worker-boundary operations a normal Tune function
needs before reporting:

1. every live Clan member exchanges fitness and agrees which process may attach the
   continuation checkpoint; and
2. the selected process binds the exact genome it used to that checkpoint before
   reporting it to Tune.

The controller is not the evolutionary policy owner. The Tune scheduler owns parent
selection, mutation, next-trial assignments, mutation random state, recovery, replay
lineage, and winner-checkpoint redistribution.

The active genome for a member is the controlled subset of that member's
scheduler-assigned `Trial.config`. The controller receives a copy of that mapping for
the current function invocation so it can record producer provenance if this worker
wins.

## Intended Tune function

The ordinary user flow is:

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
        model=model,
        optimizer=optimizer,
        persist=should_save,
    )

    if should_save:
        checkpoint = controller.save_genome(checkpoint)
        tune.report(metrics, checkpoint=checkpoint)
    else:
        tune.report(metrics)
```

`distributed_checkpoint_boundary()` represents the Lightning integration: every DDP
rank participates in the required checkpoint boundary, while only the selected rank
retains a persistent checkpoint.

The future `make_cbt_controller(genome=...)` integration factory will obtain rank,
population size, comparison direction, and Ray collective context from CBT runtime
metadata. The caller supplies the controlled genome because it is derived from the same
configuration applied to the optimizer.

## Controller responsibility

A controller exists for one Tune function invocation and one reporting boundary. It:

1. copies the current controlled genome mapping at construction;
2. stores one finite local fitness;
3. enters one injected population-wide fitness exchange;
4. applies the shared comparison and stable rank tie-break;
5. caches whether this process is the checkpoint source;
6. permits only the selected process to save its genome into checkpoint metadata; and
7. returns the same checkpoint reference after that metadata update.

It does not own:

- model, optimizer, or Lightning state;
- Tune checkpoint loading or reporting;
- mutation or child-genome construction;
- next-trial configuration;
- scheduler persistence, recovery, or replay;
- generation identity or Tune trial identity;
- a current or next `ClanRound`;
- round advancement; or
- serializable controller continuation.

## Core contract

The intended framework-independent constructor is:

```python
controller = ClanController(
    member_id=rank,
    population_size=world_size,
    mode="min",
    genome=genome,
    exchange_fitness=all_gather_fitness,
)
```

`genome` is copied immediately. The controller never mutates that copy and never uses it
to configure the optimizer. The training function remains responsible for applying the
same supplied genome to the optimizer.

`exchange_fitness(local_fitness)` must block until every required member participates
and then return one rank-ordered fitness value per member.

```python
controller.set_fitness(local_fitness)
should_save = controller.should_save_checkpoint()
```

The first `should_save_checkpoint()` call performs the exchange. Later calls return the
cached result and do not enter the collective again.

If `should_save` is true:

```python
checkpoint = controller.save_genome(checkpoint)
```

`save_genome()` is invalid before the save decision is resolved and invalid on a losing
worker. It merges the controller's member ID and copied genome into the checkpoint's
CBT metadata and returns the same checkpoint reference.

## Checkpoint metadata

The worker writes the minimal producer record:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

The controller does not write a round index because it does not own or reliably know
the scheduler generation. It does not write a Tune trial ID because the stable Clan
member ID and exact genome are sufficient for scheduler verification.

The controller also does not write child genomes, fitness, mutation state, or lineage.
Those remain scheduler responsibilities.

## Why provenance belongs on the winner-side controller

The controller holds the exact immutable genome snapshot supplied to the worker. Once
that worker is selected, it is the narrowest object that can bind the completed
checkpoint to the values that produced it before publication.

The ordering is:

```text
Lightning constructs the selected checkpoint
→ selected controller saves its genome into metadata
→ Tune receives one complete checkpoint
```

This avoids a scheduler crash window in which Tune has received an unannotated winning
payload but the scheduler has not yet attached its producer genome.

The controller still does not become authoritative over the population. It records one
scheduler assignment; it does not choose the next assignments.

## Scheduler verification

After receiving the complete generation, the scheduler independently:

1. selects the winner from the population results;
2. verifies that exactly that member supplied the checkpoint;
3. reads the checkpoint metadata;
4. verifies that `member_id` matches the winner;
5. verifies that `genome` matches the controlled subset of the winner's active
   `Trial.config`; and
6. only then derives and commits the next population.

A mismatch invalidates the transition rather than choosing one copy arbitrarily.

## Shared selection rule

The worker and Tune scheduler must select the same rank from the same ordered fitness
population. The core therefore uses one shared `select_winner_id()` implementation so
comparison direction and stable lower-rank tie behavior cannot drift.

That selector is shared policy, not a controller type. The active package should move it
to a neutral selection module when the current transitional module layout is corrected.

## Mutation rules and module placement

`MutationSpec` is a scheduler/evolution value. It does not belong to the worker
controller and should move out of `controller_types.py`.

Likewise, scheduler transition metadata and checkpoint redistribution do not belong in
the controller namespace. The only checkpoint effect owned by the controller is
winner-side `save_genome(checkpoint)` using the controller's own immutable snapshot.

See [API reference](api.md) for the intended call surface and
[system architecture](../design/system_architecture.md) for the complete Tune,
Lightning, scheduler, provenance, and collective lifecycle.
