# Worker controller API

The active public framework-independent surface consists of `ClanController` and
`MutationSpec`.

## `ClanController`

`ClanController` is the worker-side collective checkpoint decision. It is constructed
once for one Tune function invocation and one reporting boundary.

```python
from clan_based_tuning import ClanController

controller = ClanController(
    member_id=rank,
    population_size=world_size,
    mode="min",
    exchange_fitness=all_gather_fitness,
)
```

`member_id`
: Stable zero-based member rank.

`population_size`
: Number of concurrently participating Clan members.

`mode`
: `"min"` or `"max"`. Equal fitness selects the lower member rank.

`exchange_fitness`
: Callable receiving this worker's scalar fitness and returning one rank-ordered
  fitness value for every required member. The production integration will implement
  this with the Ray collective.

The public Tune-facing integration is expected to construct this object through
`make_cbt_controller()` so ordinary users do not provide those runtime values manually.
That factory is not implemented by the framework-independent slice.

### `set_fitness(fitness)`

Stores one finite local fitness. Fitness can be assigned only once.

```python
controller.set_fitness(validation_loss)
```

This operation does not enter the collective.

### `should_save_checkpoint()`

```python
should_save = controller.should_save_checkpoint()
```

The first call:

1. requires local fitness;
2. exchanges fitness across the complete population;
3. verifies the configured population size;
4. selects one winner using the shared direction and stable rank tie-break; and
5. returns whether the local member is that winner.

The result is cached. Repeated calls return the same boolean without performing another
collective operation.

The method does not construct, load, save, wrap, annotate, or report a checkpoint. The
train function and Lightning integration use the boolean at their ordinary checkpoint
boundary.

The controller contains no genome or scheduler state. The active member genome is the
controlled subset of that member's Tune configuration.

## `MutationSpec`

```python
from clan_based_tuning import MutationSpec

lr_mutation = MutationSpec(
    standard_deviation=0.25,
    geometry="log",
    minimum=1e-5,
    maximum=1e-2,
)
```

`standard_deviation`
: Gaussian displacement scale.

`geometry`
: `"linear"` adds the displacement. `"log"` multiplies by its exponential.

`minimum`, `maximum`
: Inclusive bounds applied after mutation.

`mutation.mutate(value, random_stream)` returns one bounded mutation. The future CBT
Tune scheduler owns the random stream and applies mutation while constructing target
trial genomes. The worker controller does not use or retain mutation state.

## Internal scheduler primitives

Two framework-independent helpers are intentionally not exported from the package root.
They support the future scheduler without making policy mechanics part of the ordinary
user API.

### `select_winner_id(population, mode)`

Returns the stable winning rank from rank-ordered fitness values. The worker controller
uses this same implementation so the worker save decision and scheduler verification
cannot disagree on comparison direction or ties.

### `build_parent_genome_metadata(...)`

Builds the namespaced metadata mapping the scheduler will merge into the selected Ray
checkpoint:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "round_index": round_index,
        "source_member_id": source_member_id,
        "source_trial_id": source_trial_id,
        "parent_genome": dict(genome),
    }
}
```

The `genome` argument is the controlled subset of the winning trial's active
configuration. The helper only builds plain metadata; Ray checkpoint mutation remains a
scheduler integration responsibility.
