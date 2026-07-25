# Clan controller

Status: Milestone 2 controller contract and implementation

## Lifecycle boundary

`ClanController` runs between training rounds. An external training system owns the
live members, model and optimizer state, checkpoints, data, distributed execution,
and round timing. At a completed round it gives the controller rank-ordered fitness
values and optimizer-hyperparameter configurations. The controller selects one
parent rank and returns the next rank-ordered configurations.

The controller is not a Lightning callback, Ray scheduler, optimizer factory,
checkpoint manager, or population runtime. Milestone 3 will choose how Ray gathers
the required plain data and executes the returned decision.

## Data model

Rank is the only member identity inside the controller call:

```text
fitnesses[rank]       -> comparable fitness for that external member
configurations[rank]  -> that member's optimizer-hyperparameter mapping
```

The two sequences must have equal length and the same rank ordering. Every
configuration contains exactly the optimizer-hyperparameter names declared when
the controller was constructed. The caller owns the mapping between framework
members and ranks and is responsible for supplying the complete live Clan.

`next_generation(...)` returns:

```text
parent_rank, next_configurations
```

`parent_rank` tells the external lifecycle which member's model and optimizer state
will be inherited. `next_configurations[rank]` tells it which optimizer
hyperparameters to apply to the corresponding next-generation member. The
controller never receives or returns model parameters, optimizer objects, or
checkpoints.

## Evolution policy

The controller performs four steps:

1. Validate and normalize the complete rank-ordered input before consuming random
   numbers.
2. Select the lowest fitness in `mode="min"` or the highest fitness in
   `mode="max"`. Equal scores select the lowest rank.
3. Retain the selected parent's optimizer configuration exactly at the parent
   rank. This preserves one incumbent control rather than risking the selected
   policy entirely to mutation.
4. Independently mutate every other rank from that same parent configuration.

Initialization uses the same control principle: rank zero receives the declared
defaults and every other rank receives a mutation of those defaults.

### Mutation geometry

Each optimizer hyperparameter declares one geometry:

- `linear`: add `Normal(0, standard_deviation)` in value units;
- `log`: multiply by `exp(Normal(0, standard_deviation))`.

The result is clamped to the declared inclusive minimum and maximum. Mutation is
local around the selected parent; the controller does not resample from a global
search distribution.

## Randomness and persistence

The constructor creates a private `random.Random` stream from the supplied seed.
Redundant controllers with the same policy, seed, and valid call sequence produce
the same decisions. Validation completes before mutation, so a rejected generation
does not advance the stream.

`state_dict()` and `load_state_dict(...)` expose only the evolving random-stream
state. Hyperparameter policy and selection mode remain constructor configuration
and should be persisted by the external experiment configuration rather than
copied into a second mutable source of truth.

## Failure and ownership

The controller rejects malformed hyperparameter policy, non-finite fitness,
misaligned rank sequences, illegal configuration keys, and values outside their
declared bounds. It produces no partial generation and does not modify caller-owned
inputs.

The controller cannot independently detect a framework member omitted before the
call because it deliberately does not own framework population membership.
Milestone 3 must prove that its gather boundary supplies one entry per live rank
before invoking the controller.

See [API reference](api.md) for the concrete call surface.
