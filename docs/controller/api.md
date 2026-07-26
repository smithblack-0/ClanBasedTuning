# Clan controller API

The Milestone 2 surface consists of `Population` and `ClanController`. Both use
ordinary Python dictionaries and scalars and have no Ray or Lightning dependency.

## `Population`

`Population(configurations, fitness={})` represents one complete rank-indexed
generation.

```python
from clan_based_tuning import Population

population = Population(
    configurations={
        0: {"lr": 3e-4, "weight_decay": 0.01},
        1: {"lr": 4e-4, "weight_decay": 0.008},
    }
)
```

### Structure

```text
configurations[rank] = optimizer-hyperparameter dictionary
fitness[rank]        = finite comparable score, when available
```

Configuration keys must be contiguous ranks beginning at zero. Population
construction copies the supplied configuration dictionaries and validates only this
outer structure. It deliberately trusts the contained optimizer values; a future
framework adapter must validate external values before construction.

### Methods

`population.ranks`
: Stable `range` covering all ranks.

`len(population)`
: Number of ranks.

`population.get_configuration(rank)`
: Return a copy of one rank's optimizer configuration.

`population.set_fitness(rank, value)`
: Record a finite real fitness for an existing rank.

`population.get_fitness(rank)`
: Return the rank's score, or raise if it has not been set.

`population.missing_fitness_ranks()`
: Return a tuple of ranks that have not reported fitness.

## `ClanController` construction

```python
from clan_based_tuning import ClanController

controller = ClanController(
    population_size=4,
    hyperparameters={
        "lr": {
            "default": 3e-4,
            "standard_deviation": 0.25,
            "geometry": "log",
            "minimum": 1e-5,
            "maximum": 1e-2,
        },
        "weight_decay": {
            "default": 0.01,
            "standard_deviation": 0.005,
            "geometry": "linear",
            "minimum": 0.0,
            "maximum": 0.1,
        },
    },
    mode="min",
    seed=17,
)
```

`population_size`
: Fixed number of ranks expected by every population passed to this controller.

`hyperparameters`
: Dictionary mapping controlled optimizer-hyperparameter names to specifications.
  Each specification contains exactly `default`, `standard_deviation`, `geometry`,
  `minimum`, and `maximum`.

`mode`
: `"min"` or `"max"`. Equal scores select the lowest rank.

`seed`
: Integer used to create the reproducible private random stream.

The constructor validates this immutable policy once. Numeric policy fields must be
finite real scalars; logarithmic bounds must be positive.

## `initial_population()`

Create a `Population` with exactly `population_size` ranks.

```python
population = controller.initial_population()
```

Rank zero receives exact defaults. Remaining ranks receive independent local
mutations. The returned population has no fitness values set.

## `next_generation(population)`

Select one parent and create the next `Population`.

```python
for rank in population.ranks:
    population.set_fitness(rank, measured_fitness[rank])

parent_rank, next_population = controller.next_generation(population)
```

Preconditions enforced here:

- `population` is a `Population`;
- its size equals the constructor-declared population size; and
- every rank has a fitness value.

The method does not revalidate every configuration field. Controller-generated
populations are trusted; Milestone 3 must validate externally constructed
populations at its framework boundary.

Postconditions:

- exactly one parent rank is returned;
- the parent configuration is copied exactly at that rank;
- every other rank is independently mutated from the parent;
- a fresh `Population` of the same size is returned; and
- the new population has no fitness values set.

The external lifecycle uses `parent_rank` to inherit model and optimizer state. The
controller does not perform that inheritance.

## `state_dict()` and `load_state_dict(state)`

`state_dict()` returns the pseudorandom stream state needed to continue mutation
identically after external persistence. Recreate the controller with the same
population size, hyperparameter policy, and mode, then restore before the next
transition:

```python
saved_state = controller.state_dict()

restored = ClanController(
    population_size=4,
    hyperparameters=hyperparameter_policy,
    mode="min",
    seed=0,
)
restored.load_state_dict(saved_state)
```

The state mapping intentionally does not duplicate constructor policy.

## Milestone 3 handoff

Milestone 3 orchestration must:

1. establish the complete live trial set and authoritative trial-to-rank mapping;
2. validate and extract controlled optimizer configurations from framework state;
3. construct or update the corresponding `Population`;
4. write each reported fitness through `set_fitness`;
5. invoke `next_generation`; and
6. apply the returned parent and configuration decision through native framework
   lifecycle.

Those framework checks are intentionally not duplicated inside the trusted
controller path.
