# Clan controller

Status: accepted Milestone 2 design; implementation under review

`ClanController` is the framework-independent evolutionary policy for ClanBasedTuning.
It initializes optimizer configurations, selects the sole parent from one completed
population, and emits the optimizer configurations for the next generation.

It does not collect live reports, communicate between devices, transfer checkpoints,
apply configurations to optimizers, or own Ray, Lightning, or training lifecycle.
Those remain execution responsibilities for later integration.

## Policy setup

The constructor receives the expected `population_size`, fitness `mode`, and a mapping
from optimizer field name to five required values:

- `default`: the viable starting value;
- `std`: the standard deviation of local perturbation;
- `sampling`: `"linear"` for additive movement or `"log"` for log-space movement;
- `lower`: inclusive lower bound; and
- `upper`: inclusive upper bound.

Linear parameters use additive normal perturbation. Log parameters use normal
perturbation in log coordinates, which is multiplication in ordinary coordinates.
Generated values are constrained to their declared bounds.

The controller supports only finite real scalar optimizer fields in this milestone.
The configuration supplied for every member must contain exactly the fields declared
by the controller. Model, data, batch, and augmentation choices are outside the
accepted variation surface.

## Public operations

```python
from clan_based_tuning import ClanController

controller = ClanController(
    population_size=2,
    parameters={
        "lr": {
            "default": 3e-4,
            "std": 0.25,
            "sampling": "log",
            "lower": 1e-5,
            "upper": 1e-2,
        },
    },
    mode="min",
)

initial_configs = controller.initialize(["member-a", "member-b"], seed=7)

parent_id, next_configs = controller.advance(
    {
        "member-a": {"fitness": 0.42, "config": initial_configs["member-a"]},
        "member-b": {"fitness": 0.38, "config": initial_configs["member-b"]},
    },
    seed=8,
)
```

`initialize()` requires exactly the configured number of unique member IDs and returns
one complete configuration mapping. The lexicographically first member retains the
exact defaults; the remaining members receive local mutations around them.

`advance()` requires exactly the configured population size, validates every result,
selects the best fitness under `min` or `max` mode, retains that member's exact
configuration, and mutates copies for every other member. Equal fitness is resolved by
lexicographically smaller member ID.

The controller has no hidden mutable state. Explicit seeds make redundant controller
instances produce the same result from the same logical inputs, independent of input
mapping order. Failed calls return no partial transition and cannot change later
behavior.

## Framework boundary

A later execution owner must gather the plain population mapping, call `advance()`,
transfer the selected parent's training state, and apply each emitted configuration.
Milestone 2 intentionally does not choose or implement the Ray invocation seam.

Run the standalone example with:

```bash
python examples/clan_controller.py
```
