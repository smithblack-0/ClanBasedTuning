# Initial framework-managed distributed context

Status: accepted initial implementation direction  
Framework basis: Ray Tune, Lightning, and native PyTorch DDP

## Authority

This document chooses the first implementation direction for the accepted
[integration design](../design/integration.md),
[population-resolution invariants](../contracts/population_resolution_invariants.md), and
[responsibility boundaries](../contracts/population_resolution_responsibilities.md).

It is not architecture. Framework evidence may change the exact Ray and Lightning seams
without reopening those authorities, provided the replacement preserves them and is
qualified directly.

## Decision

The initial supported topology is:

```text
one live Ray Tune trial
    = one stable Clan member
    = one externally launched Lightning training process
    = one rank in the native PyTorch DDP group spanning the Clan
```

Ray Tune creates and resources the trial processes. ClanBasedTuning coordinates the
complete cohort and supplies stable member and distributed-topology facts. Lightning and
PyTorch establish, use, and tear down the DDP process group.

ClanBasedTuning does not create a separate Ray collective group for population
resolution.

## Cohort admission

The complete configured Clan must be concurrently admitted before any member blocks in
distributed initialization. A partial Clan may not occupy resources indefinitely while
waiting for members that Tune cannot schedule.

The CBT Tune scheduler or its narrow integration must therefore coordinate the native Ray
resource and trial lifecycle so the complete cohort can enter the same distributed run.

The exact mechanism is not selected here. Direct framework work must determine the
smallest native seam that can provide cohort admission without replacing Tune's trial
execution or resource ownership.

## Distributed topology handoff

Each trial must receive the facts required by Lightning's externally launched process
model, including:

- stable Clan member identity;
- distributed rank and world size;
- local device assignment supplied by the framework;
- rendezvous information for the one Clan DDP group; and
- the generation or cohort identity needed to prevent cross-generation reuse.

The worker integration presents those facts through a supported Lightning environment or
strategy seam. It does not call PyTorch distributed initialization directly.

Stable member identity and distributed rank may use the same integer in the first path,
but their association remains explicit so later topologies are not forced to equate them.

## Framework ownership

Lightning and PyTorch own:

- backend selection appropriate to the qualified device path;
- process-group initialization and teardown;
- gradient reduction and ordinary DDP synchronization;
- barriers and collective execution;
- distributed exceptions and cleanup; and
- device-local behavior required by the selected strategy.

ClanBasedTuning supplies only the missing Clan facts and policy. It does not take over
GLOO, NCCL, CUDA, rendezvous, process-group, or generic DDP lifecycle.

## Population resolution

At the qualifying round boundary, every member already belongs to the established DDP
context. The population operation uses that context to exchange one finite local fitness
per member and produce complete fitness associated with stable member identity.

The first implementation must choose the narrowest supported Lightning or PyTorch
collective surface that preserves:

- one contribution per required member;
- stable member association;
- comparison semantics for supported fitness values;
- one operation per controller boundary; and
- surfaced failure rather than partial-population selection.

The exact collective call, tensor or object representation, payload dtype, and internal
collaborator interface remain open until direct evidence selects them.

`ClanController` applies the shared deterministic selection policy after the complete
association is available. Distributed communication does not own winner policy.

## Lifecycle and failure

The complete Clan must remain in one coherent distributed lifecycle across shared
training and the population boundary. Tune may not independently advance, pause, restore,
or replace one trial while its peers remain inside the active group.

A missing or failed member invalidates the boundary. Framework and scheduler integration
must surface the failure, release or fail peers through supported lifecycle behavior, and
prevent a checkpoint or next generation from being accepted from a reduced Clan.

The exact timeout, cancellation, and recovery mechanisms depend on the qualified Ray,
Lightning, and PyTorch path. They must not be implemented by creating a second custom
communication system.

## Public and internal surfaces

The implementation must support the accepted `make_cbt_controller(genome=...)` public
flow without exposing ranks, rendezvous, process groups, or transport buffers to the user
training function.

This decision does not freeze:

- the scheduler superclass or Ray cohort-admission hook;
- the Lightning cluster-environment or strategy class;
- internal topology value objects;
- the population-exchange collaborator interface;
- the collective operation or payload representation; or
- additional advanced factory arguments.

Those details may change when the same ownership and behavior are preserved.

## Later ClanFSDP extension

The initial DDP topology has one training process per Clan member. A later ClanFSDP
system may require both a model-shard dimension and a Clan-member dimension, with
framework-owned groups or a process mesh that serves both.

That extension is deliberately deferred. It requires its own implementation and
qualification decision and must not be approximated now by introducing a second
population process group into the DDP path.

## Superseded direction

The former decision to create a package-owned Ray collective group solely for population
resolution is rejected. It duplicated framework lifecycle, hard-coded an unnecessary
communication layer, and separated population exchange from the distributed context that
already spans the Clan.

Isolated tests of Ray or GLOO scalar exchange may be useful framework observations, but
they do not establish the accepted production topology.
