# Worker controller API

Status: active framework-independent API

## `ClanController`

`ClanController` stores one worker's local fitness and caches whether that worker is the
checkpoint source for the current reporting boundary.

```python
from clan_based_tuning import ClanController

controller = ClanController(
    resolve_checkpoint_source=checkpoint_source_resolver,
)
```

`resolve_checkpoint_source`
: Callable receiving one finite local fitness and returning a Python `bool`. `True`
  means this worker is the sole checkpoint source. The callable owns any
  population-wide synchronization, comparison, membership, ordering, timeout, and
  failure handling required to produce that answer.

The controller does not prescribe a communication backend. No production resolver is
currently implemented.

### `set_fitness(fitness)`

```python
controller.set_fitness(validation_loss)
```

Stores one finite local fitness. Fitness can be assigned only once. This method does not
invoke the checkpoint-source resolver.

### `should_save_checkpoint()`

```python
should_save = controller.should_save_checkpoint()
```

The first call:

1. requires local fitness;
2. calls `resolve_checkpoint_source(local_fitness)`;
3. requires the resolver to return `bool`;
4. caches the result; and
5. returns it.

Later calls return the cached Boolean without invoking the resolver again.

The method does not gather fitness values, choose a winner, construct a checkpoint,
annotate a checkpoint, or report to Tune.

## Population-resolution boundary

The injected resolver must eventually satisfy the governing architecture:

- one result from every required stable member;
- one accepted comparison and tie rule;
- exactly one checkpoint source;
- no partial-population advance;
- no cross-generation mixing; and
- failure or timeout that releases the full population.

The concrete transport and runtime API remain open. A fake resolver used in unit tests
proves only local controller caching and validation.

## Planned producer-provenance extension

The architecture intends a later API shaped around:

```python
controller = make_cbt_controller(genome=controlled_subset(config))
...
if controller.should_save_checkpoint():
    checkpoint = controller.save_genome(checkpoint)
```

That extension is not active. It must add the copied genome mapping, stable member
identity, exact producer metadata, implementation tests, framework evidence, and matching
documentation in one reviewable sequence.

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
trial genomes.

## Internal evolution primitive

### `select_winner_id(population, mode)`

Returns the stable winning member index from an ordered fitness population. It lives in
`evolution.py` beside `MutationSpec`.

A future population-resolution implementation and the Tune scheduler may share this
helper. `ClanController` itself does not import it or inspect population fitness.
