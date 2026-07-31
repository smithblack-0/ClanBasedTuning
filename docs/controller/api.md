# Worker controller API

Status: intended corrected Milestone 3 API

The public framework-independent surface remains centered on `ClanController`. The
current implementation still needs the genome and `save_genome()` additions described
here before this API is complete.

## `ClanController`

`ClanController` is the worker-side collective checkpoint decision plus winner-side
producer-genome annotation. It is constructed once for one Tune function invocation and
one reporting boundary.

```python
from clan_based_tuning import ClanController

controller = ClanController(
    member_id=rank,
    population_size=world_size,
    mode="min",
    genome=genome,
    exchange_fitness=all_gather_fitness,
)
```

`member_id`
: Stable zero-based Clan member rank.

`population_size`
: Number of concurrently participating Clan members.

`mode`
: `"min"` or `"max"`. Equal fitness selects the lower member rank.

`genome`
: Mapping containing exactly the controlled values assigned to this worker for the
  current round. The controller copies the mapping at construction and never mutates or
  applies it.

`exchange_fitness`
: Callable receiving this worker's scalar fitness and returning one rank-ordered
  fitness value for every required member. The production integration will implement
  this with the Ray collective.

The public Tune-facing integration is expected to construct this object through:

```python
controller = make_cbt_controller(genome=genome)
```

That factory hides rank, world size, mode, and collective construction. The caller
supplies the controlled genome derived from the same configuration applied to the
optimizer.

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

The method does not construct, load, wrap, annotate, or report a checkpoint.

### `save_genome(checkpoint)`

```python
if controller.should_save_checkpoint():
    checkpoint = controller.save_genome(checkpoint)
```

This method is valid only when the controller has resolved that the local member is the
winner.

It merges this mapping into the checkpoint metadata:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": copied_genome,
    }
}
```

It returns the same checkpoint reference.

It does not:

- construct the Lightning checkpoint;
- deserialize or modify the checkpoint payload;
- report the checkpoint to Tune;
- write a round index or Tune trial ID;
- write fitness;
- derive child genomes; or
- persist scheduler mutation or lineage state.

Calling `save_genome()` before the save decision is resolved, or on a losing member, is
an error. The checkpoint object's public metadata operation is allowed to fail directly
if the supplied genome is not serializable or the backing storage cannot be updated.

## Genome authority

The Tune scheduler is the evolutionary authority. It decides the current and next
population genomes, mutation state, lineage, and recovery behavior.

For an active worker, `Trial.config` contains the scheduler's materialized genome
assignment. The controller contains an immutable copy used only to prove which values
produced the winner checkpoint.

The scheduler must verify the checkpoint's `member_id` and `genome` against the selected
winner and its active trial configuration before accepting the transition.

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

`mutation.mutate(value, random_stream)` returns one bounded mutation. The CBT Tune
scheduler owns the random stream and applies mutation while constructing target trial
genomes. The worker controller does not use or retain mutation state.

`MutationSpec` remains temporarily exported but belongs to an evolution or
scheduler-types module rather than `controller_types.py`.

## Shared selection primitive

### `select_winner_id(population, mode)`

Returns the stable winning rank from rank-ordered fitness values. The worker controller
and scheduler use the same implementation so checkpoint-source selection and scheduler
verification cannot disagree on comparison direction or ties.

This helper belongs in a neutral selection module, not in a module named for controller
types.

## Removed metadata builder

The previous `build_parent_genome_metadata(...)` design included round identity, trial
identity, and parent-genome construction for a later scheduler-side checkpoint update.
That shape is superseded.

Producer metadata is now written by the selected controller before reporting and
contains only:

- schema version;
- stable member ID; and
- the controller's copied current genome.
