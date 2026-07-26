# Clan controller API

The Milestone 2 surface consists of five framework-independent objects:
`MutationSpec`, `ControllerPolicy`, `PopulationMember`, `Population`, and
`ClanController`.

## `MutationSpec`

```python
from clan_based_tuning import MutationSpec

lr_mutation = MutationSpec(
    default=3e-4,
    standard_deviation=0.25,
    geometry="log",
    minimum=1e-5,
    maximum=1e-2,
)
```

A spec owns the initialization, mutation geometry, and bounds for one value. The
hyperparameter name is supplied by its key in `ControllerPolicy.mutations`.

`mutation.mutate(value, random_stream)` applies one bounded local mutation. Most
users call this indirectly through `ClanController`.

## `ControllerPolicy`

```python
from clan_based_tuning import ControllerPolicy

policy = ControllerPolicy(
    population_size=4,
    mutations={"lr": lr_mutation},
    mode="min",
    seed=17,
)
```

`population_size`
: Fixed number of ranks.

`mutations`
: Dictionary from the controller's hyperparameter name to a `MutationSpec`.

`mode`
: `"min"` or `"max"`. Equal fitness values select the lowest rank.

`seed`
: Seed passed to the controller's private random stream.

## `PopulationMember`

```python
from clan_based_tuning import PopulationMember

member = PopulationMember(
    hyperparameters={"lr": 3e-4},
)
member.set_fitness(0.71)
```

`hyperparameters` is the controller-side projection of current values for the names
in the policy. It is not a full optimizer configuration. The class copies the
supplied dictionary but deliberately does not interpret its origin or inspect every
contained value.

`fitness` is `None` until reported. `set_fitness(value)` records one finite
comparable score.

## `Population`

```python
from clan_based_tuning import Population

population = Population(
    members={
        0: PopulationMember({"lr": 3e-4}),
        1: PopulationMember({"lr": 4e-4}),
    }
)
```

`members[rank]` associates one stable controller rank with one `PopulationMember`.
Ranks must be contiguous from zero.

`population.ranks`
: Stable `range` covering every rank.

`len(population)`
: Number of ranks.

`population.set_fitness(rank, value)`
: Delegate one reported score to that rank's member.

`population.missing_fitness_ranks()`
: Return ranks whose members still have `fitness is None`.

## `ClanController`

```python
from clan_based_tuning import ClanController

controller = ClanController(policy)
population = controller.initial_population()
```

The constructor requires a `ControllerPolicy`. `initial_population()` creates one
member per policy rank. Rank zero receives exact defaults; the remaining ranks
receive independent mutations of those defaults.

### `next_generation(population)`

```python
for rank in population.ranks:
    population.set_fitness(rank, measured_fitness[rank])

parent_rank, next_population = controller.next_generation(population)
```

The method checks only the trusted boundary:

- the argument is a `Population`;
- its size equals `policy.population_size`; and
- every member has reported fitness.

It selects one parent, copies that parent's hyperparameter values at the parent
rank, mutates every other rank, and returns a fresh population with no fitness set.
It does not inspect external optimizer structure or revalidate every member value.

### `state_dict()` and `load_state_dict(state)`

These methods save and restore only the private random-stream state. Recreate the
controller with the same immutable `ControllerPolicy` before loading the state.

## Milestone 3 handoff

Milestone 3 orchestration must:

1. establish the complete live member set and authoritative rank mapping;
2. determine the controller hyperparameter values represented by each framework
   member;
3. validate those external values and other framework invariants;
4. construct `PopulationMember` and `Population` objects;
5. attach reported fitness;
6. call `next_generation`; and
7. apply the parent and evolved values through the native framework lifecycle.

Those responsibilities are not duplicated inside the trusted Milestone 2 data
objects or controller transition.
