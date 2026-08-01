# Worker controller API

Status: exact current framework-independent API  
Date: 2026-07-31

This file documents what the active package implements today. It does not present the
provisional callback as the accepted future Ray interface.

## `ClanController`

```python
from clan_based_tuning import ClanController

controller = ClanController(
    member_id=member_id,
    population_size=population_size,
    mode="min",
    exchange_fitness=exchange_fitness,
)
```

### `member_id`

Zero-based local identity used by the current framework-independent implementation.

The production Ray design still must prove whether this identity is exactly Ray
collective rank or is associated explicitly with that rank.

### `population_size`

Expected number of values returned by the current callback.

This constructor field is provisional. The future Ray runtime may own population size
without exposing it directly to `ClanController`.

### `mode`

`"min"` or `"max"`. Equal fitness selects the lower current sequence position through
`select_winner_id()`.

Selection policy remains required, but its final placement relative to the controller
and Ray runtime is under review.

### `exchange_fitness`

A callable with the current test seam:

```python
exchange_fitness(local_fitness) -> Sequence[float]
```

The first `should_save_checkpoint()` call invokes it once. The current implementation
assumes:

- the returned sequence contains exactly `population_size` values;
- sequence position corresponds to stable member identity; and
- every value is finite.

This is not an accepted production collective contract. It does not define Ray group
membership, rank mapping, generation isolation, timeout, missing-member failure, or
transport behavior.

## `set_fitness(fitness)`

```python
controller.set_fitness(validation_loss)
```

Stores one finite local fitness.

Current behavior:

- fitness can be assigned only once;
- non-finite values fail before the callback is invoked; and
- the method performs no communication.

## `should_save_checkpoint()`

```python
should_save = controller.should_save_checkpoint()
```

Current first-call behavior:

1. require previously assigned local fitness;
2. invoke the provisional callback;
3. require the configured sequence length;
4. require finite returned values;
5. apply `select_winner_id(population, mode)`; and
6. cache whether the selected sequence position equals `member_id`.

Later calls return the cached Boolean and do not invoke the callback again.

The caching behavior is an accepted requirement because later producer-provenance guards
must not enter a second Ray collective.

The current callback, sequence result, identity assumption, and constructor split remain
provisional.

## Not currently implemented

The active controller does not yet implement:

- a genome constructor argument;
- an independently copied genome mapping;
- `save_genome(checkpoint)`;
- Ray collective group construction;
- `make_cbt_controller()`;
- timeout or distributed failure handling; or
- generation isolation.

## Planned producer metadata

After the Ray population-resolution interface is accepted, the selected worker will
record:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

before reporting the checkpoint.

That future operation will:

- require the already cached local save decision to be `True`;
- perform no second Ray collective;
- preserve unrelated checkpoint metadata and payload;
- return the same checkpoint reference unless framework evidence requires a different
  public contract; and
- write no generation index, Tune trial ID, fitness, child genomes, mutation state, or
  lineage.

The exact method name and checkpoint API remain subject to the later provenance
implementation review.

## Framework-independent evolution API

### `MutationSpec`

```python
from clan_based_tuning import MutationSpec

lr_mutation = MutationSpec(
    standard_deviation=0.25,
    geometry="log",
    minimum=1e-5,
    maximum=1e-2,
)
```

`MutationSpec` lives in `evolution.py` and belongs to scheduler/evolution policy rather
than worker-controller state.

### `select_winner_id(population, mode)`

`select_winner_id()` lives in `evolution.py` and defines the current deterministic
minimizing/maximizing and lower-position tie rule.

The accepted architecture requires one shared pure selection policy for worker-side Ray
resolution and scheduler verification. The final member-associated input type may change
when the stable identity contract is designed; the current sequence input is not
necessarily the final public form.

## Design reference

See [Ray population-resolution design](../design/population_resolution.md) for the fixed
requirements and open interface choices that govern the replacement.
