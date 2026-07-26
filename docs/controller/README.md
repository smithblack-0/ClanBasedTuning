# Clan controller

Status: Milestone 2 controller contract and implementation

## Lifecycle boundary

`ClanController` runs between training rounds. An external training system owns the
live members, model and optimizer state, checkpoints, data, distributed execution,
and round timing. The controller owns only the evolutionary policy: create one
initial `Population`, select one parent from a completed population, and create the
next population of optimizer-hyperparameter configurations.

The controller is not a Lightning callback, Ray scheduler, optimizer factory,
checkpoint manager, or population runtime. Milestone 3 orchestration will connect
framework-owned trials to the named data structures below.

## Named data contracts

The module defines three contracts before `ClanController` uses them.

### Hyperparameter policy

A dictionary keyed by optimizer-hyperparameter name:

```text
hyperparameters[name] = {
    "default": finite real,
    "standard_deviation": positive finite real,
    "geometry": "linear" | "log",
    "minimum": finite real,
    "maximum": finite real,
}
```

The controller validates and copies this immutable policy once during construction.
`population_size`, metric direction, and random-seed validity are also constructor
contracts.

### Optimizer configuration

A dictionary containing the controlled optimizer values for one rank:

```text
configuration[name] = current value
```

Controller-generated configurations satisfy the policy. Milestone 3 orchestration
must validate an externally gathered trial configuration before placing it into a
`Population`; the controller does not repeatedly audit every configuration on each
generation.

### `Population`

`Population` is the internal domain data structure for one complete generation. It
is a dataclass backed by two dictionaries:

```text
population.configurations[rank] = optimizer configuration
population.fitness[rank]        = comparable fitness, when reported
```

Configuration ranks are exactly contiguous integers from `0` through
`len(population) - 1`. A missing fitness key means that rank has not reported for
the current generation.

Population construction validates the outer dictionary/rank structure once and
copies the configuration dictionaries. It does not validate framework membership,
hyperparameter names, or optimizer bounds. Those are already true for
controller-generated populations and must be established by Milestone 3 before it
constructs a population from framework data.

The supported interaction is:

- `population.get_configuration(rank)` returns a copy of one configuration;
- `population.set_fitness(rank, value)` records one finite score;
- `population.get_fitness(rank)` returns a reported score; and
- `population.missing_fitness_ranks()` reports incomplete ranks.

`Population` does not own live trials or training state. Rank remains the temporary
association between this data structure and framework-owned members.

## Generation lifecycle

A direct lifecycle is:

```python
controller = ClanController(
    population_size=4,
    hyperparameters=hyperparameter_policy,
    mode="min",
    seed=17,
)

population = controller.initial_population()

for rank in population.ranks:
    configuration = population.get_configuration(rank)
    fitness = train_or_evaluate_member(rank, configuration)
    population.set_fitness(rank, fitness)

parent_rank, population = controller.next_generation(population)
```

`initial_population()` creates exactly the constructor-declared number of ranks.
Rank zero receives the declared defaults and every other rank receives an
independent mutation of those defaults.

`next_generation(population)` performs only call-time checks that cannot be settled
at construction:

1. the argument is a `Population`;
2. its size matches the controller's fixed population size; and
3. every rank has reported fitness.

It then selects the parent, retains that configuration exactly at the parent rank,
mutates every other rank from the parent, and returns a fresh `Population` with no
fitness values set.

## Evolution policy

The lowest fitness wins in `mode="min"`; the highest wins in `mode="max"`. Equal
fitness values select the lowest rank.

Each optimizer hyperparameter declares one mutation geometry:

- `linear`: add `Normal(0, standard_deviation)` in value units;
- `log`: multiply by `exp(Normal(0, standard_deviation))`.

The result is clamped to the declared inclusive minimum and maximum. Mutation is
local around the selected parent; the controller does not resample from a global
search distribution.

## Validation ownership

Validation is intentionally allocated by lifecycle rather than repeated everywhere.

| Owner | Validation |
| --- | --- |
| `ClanController` construction | Population size, immutable mutation policy, metric direction, and seed. |
| `Population` construction | Dictionary shape, contiguous ranks, configuration dictionaries, and copied ownership. |
| `Population.set_fitness` | Existing rank and finite scalar fitness. |
| `ClanController.next_generation` | Population type, fixed size, and complete fitness only. |
| Milestone 3 orchestration | Complete live trial set, unique authoritative rank mapping, framework result extraction, controlled optimizer fields, and externally sourced configuration legality before constructing `Population`. |

This split treats the tightly coupled controller/Population path as trusted while
keeping defensive framework validation at the actual external boundary.

## Randomness and persistence

The controller creates a private `random.Random` stream from the supplied seed.
Redundant controllers with the same policy, seed, and valid call sequence produce
the same decisions. Failure for wrong type, wrong size, or missing fitness occurs
before mutation and does not advance the stream.

`state_dict()` and `load_state_dict(...)` expose only the evolving random-stream
state. Hyperparameter policy, population size, and selection mode remain constructor
configuration and should be persisted by the external experiment configuration.

See [API reference](api.md) for the concrete call surface.
