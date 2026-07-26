# Clan controller

Status: Milestone 2 controller contract and implementation

## Lifecycle boundary

`ClanController` runs between training rounds. It owns selection, mutation, and the
random stream used to produce the next generation. It does not own trials, model or
optimizer state, checkpoints, distributed communication, or framework lifecycle.

Milestone 3 orchestration owns the external boundary. It determines which framework
values correspond to the controller's named hyperparameters, validates that external
state, and constructs the trusted objects below.

## Data meaning

The controller does not define an optimizer configuration format. It works with a
small projection of values whose meaning is explicit in the following dataclasses.

### `MutationSpec`

One `MutationSpec` describes how one named hyperparameter is initialized and mutated:

- `default`: first-generation value;
- `standard_deviation`: local Gaussian mutation scale;
- `geometry`: `"linear"` or `"log"`;
- `minimum`: inclusive lower bound; and
- `maximum`: inclusive upper bound.

The name comes from the key in `ControllerPolicy.mutations`. The class validates
only the numeric relationships that make its own mutation rule meaningful.

### `ControllerPolicy`

`ControllerPolicy` composes the immutable settings for one controller:

```text
population_size
mutations[name] -> MutationSpec
mode             -> "min" | "max"
seed
```

It validates only its immediate contract: usable population size, at least one
mutation, supported metric direction, and `MutationSpec` children.

### `PopulationMember`

A `PopulationMember` is the controller-side data for one rank:

```text
member.hyperparameters[name] -> current value evolved by the controller
member.fitness               -> comparable score, or None before reporting
```

`hyperparameters` is not a full optimizer configuration and carries no claim about
where the value came from. Milestone 3 decides how framework state is projected into
this dictionary. The member copies that dictionary and validates only a fitness when
one is attached.

### `Population`

A `Population` composes one generation:

```text
population.members[rank] -> PopulationMember
```

Ranks are contiguous integers beginning at zero. Construction checks only this rank
shape and that each child is a `PopulationMember`. It does not inspect every
hyperparameter name or value.

## Direct lifecycle

```python
from clan_based_tuning import (
    ClanController,
    ControllerPolicy,
    MutationSpec,
)

policy = ControllerPolicy(
    population_size=4,
    mutations={
        "lr": MutationSpec(
            default=3e-4,
            standard_deviation=0.25,
            geometry="log",
            minimum=1e-5,
            maximum=1e-2,
        )
    },
    mode="min",
    seed=17,
)
controller = ClanController(policy)
population = controller.initial_population()

for rank in population.ranks:
    values = population.members[rank].hyperparameters
    fitness = train_or_evaluate_member(rank, values)
    population.set_fitness(rank, fitness)

parent_rank, population = controller.next_generation(population)
```

The next population retains the selected parent's values at its rank, mutates every
other rank from that parent, and begins with all fitness values unset.

## Validation ownership

Validation follows ownership rather than forming a parallel hierarchy:

| Owner | Local validation |
| --- | --- |
| `MutationSpec` | Its mutation geometry and numeric relationships. |
| `ControllerPolicy` | Its immediate fixed settings and `MutationSpec` children. |
| `PopulationMember` | Its dictionary field and an attached finite fitness. |
| `Population` | Contiguous ranks and `PopulationMember` children. |
| `ClanController.next_generation` | Correct object type, fixed size, and complete fitness. |
| Milestone 3 orchestration | External membership, rank authority, extraction, optimizer interpretation, and all framework consistency checks. |

The trusted controller path deliberately does not repeat external validation.
Malformed hyperparameter dictionaries inside a manually constructed member violate
the documented internal contract and may fail naturally when used.

## Evolution policy

The lowest fitness wins in `mode="min"`; the highest wins in `mode="max"`. Equal
fitness values select the lowest rank.

Linear mutation adds a Gaussian displacement. Log mutation multiplies by the
exponential of that displacement. `MutationSpec` clamps either result to its bounds.

## Randomness and persistence

The controller creates a private `random.Random` stream from the policy seed.
`state_dict()` and `load_state_dict(...)` expose only that evolving stream state.
The immutable `ControllerPolicy` remains external experiment configuration.

See [API reference](api.md) for the concrete call surface.
