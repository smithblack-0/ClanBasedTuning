# Public API

Status: current and accepted intended surface

## Purpose

This document records the public lowering through which application and integration code
use ClanBasedTuning. It distinguishes implemented behavior from accepted surface that is
not yet connected to the production Ray Tune and Lightning integration.

It does not specify internal population-exchange collaborators, helper functions, module
layout, distributed backend, or framework hooks that may change during implementation.

## Worker flow

The accepted worker-facing flow is:

```python
controller = make_cbt_controller(genome=genome)
controller.set_fitness(fitness)

if controller.should_save_checkpoint():
    checkpoint = controller.save_genome(checkpoint)
```

`set_fitness()` and `should_save_checkpoint()` are implemented on `ClanController` now.
The production factory and winner-side `save_genome()` path remain to be implemented.

## `make_cbt_controller(genome=...)`

This is the intended public integration constructor. The caller supplies the controlled
optimizer configuration assigned to the current member. The integration supplies stable
member identity, population membership, comparison mode, generation context, and access
to the population exchange over the already-established framework-managed distributed
context.

The name and `genome` argument express the accepted public flow. Additional arguments,
configuration objects, or advanced construction paths may be added when implementation
evidence requires them. The factory must not make users manually construct distributed
groups, choose a backend, supply rendezvous details, or assemble transport collaborators
for the ordinary path.

The factory does not itself initialize or tear down the Lightning/PyTorch distributed
context. That lifecycle remains with the framework integration that launches the Tune
trial as one member process.

Direct `ClanController` construction remains useful for framework-independent testing and
advanced composition. Its current injected `exchange_fitness` constructor seam is
transitional and is not the target production signature.

## `ClanController.set_fitness(fitness)`

Stores one finite local fitness for the current population boundary.

```python
controller.set_fitness(validation_loss)
```

Fitness may be assigned only once. This operation does not enter population
communication.

## `ClanController.should_save_checkpoint()`

Returns whether the local member is the sole selected checkpoint source.

```python
should_save = controller.should_save_checkpoint()
```

The first call:

1. requires local fitness;
2. performs the complete-population exchange through the configured collaborator over
   the established framework-managed distributed context;
3. applies the shared comparison direction and deterministic tie policy; and
4. caches whether the local stable member is selected.

Repeated calls return the cached answer without a second population operation.
The method does not initialize distributed communication, construct, annotate, persist,
or report a checkpoint.

## `ClanController.save_genome(checkpoint)`

This accepted method is valid only after `should_save_checkpoint()` has resolved `True`.
It binds the selected checkpoint to the stable member and copied optimizer configuration
that produced it, then returns the same checkpoint reference.

```python
checkpoint = controller.save_genome(checkpoint)
```

The accepted producer-provenance schema is:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": copied_genome,
    }
}
```

The metadata contains only the schema version, stable member identity, and copied current
genome. It does not contain:

- Tune trial or generation state;
- fitness or comparison mode;
- child configurations;
- mutation random state;
- scheduler lineage; or
- recovery state.

The method does not construct the Lightning checkpoint or report it to Tune. Calling it
before population resolution or on a losing member is an error.

The checkpoint metadata mechanism may follow the qualified framework interface, but it
must preserve this schema and must not deserialize or modify the Lightning payload. The
CBT Tune scheduler verifies the recorded member and genome against the selected member's
active controlled configuration before accepting the transition.

## `MutationSpec`

`MutationSpec` is implemented and publicly exported.

```python
from clan_based_tuning import MutationSpec

lr_mutation = MutationSpec(
    standard_deviation=0.25,
    geometry="log",
    minimum=1e-5,
    maximum=1e-2,
)
```

- `standard_deviation` is the Gaussian displacement scale.
- `geometry="linear"` adds the displacement.
- `geometry="log"` multiplies by the exponential of the displacement.
- `minimum` and `maximum` are inclusive bounds applied after mutation.

`mutation.mutate(value, random_stream)` returns one bounded mutation. The CBT Tune
scheduler owns the random stream and mutation lifecycle. Worker controllers do not use
or retain mutation state.

## Internal policy functions

Worker and scheduler selection use one shared deterministic implementation so comparison
direction and ties cannot diverge. Its helper name, signature, module, and container types
are internal rather than public API.
