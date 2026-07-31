# Worker controller API

The active framework-independent surface consists of `ClanController` and
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
4. selects one winner using the configured direction and stable rank tie-break; and
5. returns whether the local member is that winner.

The result is cached. Repeated calls return the same boolean without performing another
collective operation.

The method does not construct, load, save, wrap, or report a checkpoint. The train
function and Lightning integration use the boolean at their ordinary checkpoint
boundary.

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
Tune scheduler owns the random stream and applies mutation while constructing next
trial configurations. The worker controller does not use or retain mutation state.
