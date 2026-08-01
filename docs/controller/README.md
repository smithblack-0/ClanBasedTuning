# Worker-side Clan controller

Status: active local checkpoint-source cache; producer provenance remains planned

## Purpose

`ClanController` stores the small amount of worker-local state needed at one reporting
boundary:

- one finite local fitness value; and
- one cached answer indicating whether this worker is the checkpoint source.

The controller does not gather population fitness, select a communication backend,
maintain group membership, or apply the evolutionary comparison itself. Those
responsibilities belong to the runtime population-resolution integration.

The Tune scheduler remains authoritative over parent selection, mutation, child genomes,
lineage, recovery, target configurations, and checkpoint redistribution.

## Current framework-independent constructor

```python
controller = ClanController(
    resolve_checkpoint_source=checkpoint_source_resolver,
)
```

`checkpoint_source_resolver(local_fitness)` is an injected runtime operation. It receives
this worker's finite local fitness and returns a Python `bool` indicating whether this
worker is the sole checkpoint source.

The resolver, not the controller, owns:

- complete-population synchronization;
- member identity and ordering;
- comparison direction and tie behavior;
- communication transport;
- timeout and failure release; and
- generation separation.

No production resolver is currently implemented. The project has not selected Ray
collectives, the existing PyTorch process group, an all-gather operation, or any other
transport.

## Current lifecycle

```python
controller.set_fitness(local_fitness)
should_save = controller.should_save_checkpoint()
```

`set_fitness()` stores one finite value and does not invoke the resolver.

The first `should_save_checkpoint()` call:

1. requires local fitness;
2. invokes `checkpoint_source_resolver(local_fitness)`;
3. requires a Boolean result;
4. caches that result; and
5. returns it.

Later calls return the cached result and do not invoke the resolver again.

This caching is the only synchronization-related behavior owned by the controller. It
prevents a later checkpoint annotation guard from repeating the population decision.

## Explicit non-ownership

The current controller does not own:

- population size or member rank;
- minimizing or maximizing mode;
- stable winner selection;
- any ordered population-fitness sequence;
- model, optimizer, or Lightning state;
- Tune checkpoint loading or reporting;
- mutation or child-genome construction;
- next-trial configuration;
- scheduler persistence, recovery, or replay;
- a current or next `ClanRound`;
- generation advancement; or
- serializable controller continuation.

`select_winner_id()` remains a pure evolutionary-policy helper in `evolution.py`. A
future population resolver may use it, but the controller does not import or invoke it.

## Intended next responsibility: producer provenance

The accepted architecture intends a later controller extension:

```python
controller = make_cbt_controller(genome=controlled_subset(config))
...
if controller.should_save_checkpoint():
    checkpoint = controller.save_genome(checkpoint)
```

That future slice will add:

- an independent copied genome mapping;
- stable member identity required by producer metadata; and
- winner-only checkpoint annotation.

It is not part of the current implementation. Rejected PR #37 must not be reused as the
implementation source.

## Why the communication seam is outside the controller

The controller needs only the final local answer before Tune reporting. It does not need
to know whether the runtime arrived at that answer by communicating all fitness values,
a winning member ID, or final local Booleans.

Keeping that mechanism outside the controller allows the current iteration to compare
the existing PyTorch process group with Ray-native options without baking an unreviewed
transport into the worker API.

See [API reference](api.md) for the exact active call surface and
[system architecture](../design/system_architecture.md) for the complete lifecycle and
open integration seam.
