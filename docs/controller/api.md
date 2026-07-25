# Clan controller API

The accepted Milestone 2 surface consists of `ClanController`. It uses only Python
real scalars, mappings, and rank-ordered sequences and has no Ray or Lightning
dependency.

## Construction

```python
from clan_based_tuning import ClanController

controller = ClanController(
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

`hyperparameters` maps optimizer-hyperparameter names to specifications with five
required fields:

| Field | Meaning |
| --- | --- |
| `default` | Initial value used before the first round. |
| `standard_deviation` | Gaussian mutation scale in value units for `linear` or natural-log units for `log`. |
| `geometry` | `"linear"` for additive mutation or `"log"` for multiplicative mutation. |
| `minimum` | Inclusive lower bound. Must be positive for `log`. |
| `maximum` | Inclusive upper bound. |

Numeric fields must be finite real scalars. Strings and booleans are not accepted
as numeric values. `mode` is `"min"` or `"max"`. `seed` must be an explicit
non-`None` value and initializes the controller's reproducible random stream.

## `initial_configurations(population_size)`

Returns one new optimizer-hyperparameter mapping per rank. `population_size` must
be an integer of at least two; booleans are not accepted as integers. Rank zero
receives exact defaults; the remaining ranks receive independent mutations of the
defaults.

```python
configurations = controller.initial_configurations(population_size=4)
```

The returned list is rank ordered and contains no framework member objects.

## `next_generation(fitnesses, configurations)`

Selects the parent and produces the next rank-ordered configurations.

```python
parent_rank, configurations = controller.next_generation(
    fitnesses=[0.83, 0.71, 0.76, 0.79],
    configurations=configurations,
)
```

Preconditions:

- both arguments are rank-ordered sequences;
- they have equal length and at least two entries;
- `fitnesses[rank]` and `configurations[rank]` describe the same external member;
- fitness values are finite real scalars, not strings or booleans;
- every configuration contains exactly the declared hyperparameter names; and
- every current hyperparameter value is a finite real scalar inside its declared
  bounds.

Postconditions:

- the return value identifies exactly one parent rank;
- the selected parent configuration is copied exactly at that rank;
- every other rank is mutated independently from the selected parent;
- the returned list has the same rank ordering and length as the input; and
- caller-owned inputs are unchanged.

The external lifecycle uses `parent_rank` to inherit model and optimizer state. The
controller does not perform that inheritance.

## `state_dict()` and `load_state_dict(state)`

`state_dict()` returns the pseudorandom stream state needed to continue mutation
identically after external persistence. Recreate the controller with the same
hyperparameter policy and mode, then restore before the next call:

```python
saved_state = controller.state_dict()

restored = ClanController(
    hyperparameters=hyperparameter_policy,
    mode="min",
    seed=0,
)
restored.load_state_dict(saved_state)
```

The state mapping intentionally does not duplicate constructor policy.

## Framework handoff

A future Ray integration must translate framework-owned results into the two
rank-ordered sequences, invoke this API, and apply the returned parent and
configuration decision through native framework lifecycle. That integration is
not part of this module.
