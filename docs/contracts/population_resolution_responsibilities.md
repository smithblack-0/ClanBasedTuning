# Population-resolution responsibilities

Status: accepted architectural contract

## Purpose

This document assigns ownership for satisfying the
[population-resolution invariants](population_resolution_invariants.md).

It fixes authority boundaries where ambiguity could duplicate policy or hide lifecycle
state. It deliberately does not freeze internal transport representation, backend,
device placement, helper names, or other implementation details that do not affect those
boundaries.

## Semantic boundary

The Ray population runtime accepts one member's local fitness at one generation boundary
and returns a complete association between stable Clan members and their fitness values.

That association is the contract. Its concrete Python type is not architectural.

A successful result contains exactly one finite comparable fitness for every required
stable member. The mapping between a Ray collective participant and a stable member is
explicit or mechanically proven; incidental sequence position is insufficient unless its
meaning is established by the runtime contract.

## Ray population runtime

The Ray-specific population runtime owns:

- collective-group construction, membership, and teardown;
- the mapping between stable member identity and collective participation;
- population communication at one qualifying generation boundary;
- returning complete member-associated fitness information;
- preventing contributions from different generations from mixing;
- surfacing timeout, participant failure, malformed transport output, and incomplete
  participation; and
- releasing waiting participants when the boundary fails.

It does not own:

- minimizing or maximizing policy;
- tie-breaking policy;
- winner selection;
- mutation or child-configuration derivation;
- scheduler lineage or recovery;
- checkpoint construction; or
- Tune result reporting.

The architecture commits to Ray collective communication for this role. The exact Ray
primitive, backend, device, dtype, internal result container, and implementation object
name are implementation decisions.

## Framework-independent selection policy

The shared selection policy owns:

- comparison direction;
- comparison-validity rules;
- stable deterministic tie behavior; and
- selection of one stable member from complete member-associated fitness.

The worker-side path and CBT Tune scheduler use the same implementation. The Ray
population runtime does not contain a second winner-selection rule.

## Worker controller

`ClanController` owns the worker-facing state and ordering:

- the stable identity of its local member;
- comparison mode;
- one local fitness value;
- one invocation of the Ray population runtime;
- application of the shared selection policy to the complete result;
- one cached local save decision; and
- copied current-configuration provenance and winner-only provenance writing.

The controller does not create or destroy Ray collective groups. It does not expose
collective membership or transport buffers to the user training function. It does not
mutate configurations, derive child configurations, advance generations, or persist Tune
transition state.

The accepted public methods and ordinary construction flow are defined in
[`../api.md`](../api.md). This contract does not fix the controller's internal
collaborator interface or concrete population-result type.

## Worker integration

The worker integration implements the accepted `make_cbt_controller(genome=...)` flow.
It obtains runtime identity, population membership, comparison configuration, generation
context, and collective configuration without requiring the user training function to
assemble those details manually.

Additional factory arguments, advanced construction paths, and internal wiring remain
open. The ordinary path and its responsibility do not: hide framework wiring while
preserving an ordinary Tune function lifecycle.

## CBT Tune scheduler

A CBT Tune scheduler exists and owns the authoritative generation transition. It:

- waits for one result from every required trial;
- associates each reported fitness with the correct stable member and active controlled
  optimizer configuration;
- applies the same shared selection policy independently;
- verifies that exactly the selected member supplied the checkpoint;
- verifies checkpoint producer provenance;
- derives child configurations;
- persists mutation random state, lineage, and recovery state;
- installs target configurations and the common selected checkpoint; and
- releases the next population only after the transition is durably accepted.

The scheduler does not trust the worker-side result as authority. Worker resolution makes
one pre-report checkpoint possible; scheduler verification decides whether the generation
transition is accepted.

The scheduler's exact Ray superclass, delegated native scheduler machinery, persistence
seam, and hook methods remain open to direct framework evidence.

## Lightning and PyTorch

Lightning owns training-loop cadence, the qualifying validation-and-checkpoint boundary,
checkpoint construction, and restoration. Native PyTorch DDP owns shared-gradient
communication for the supported initial path.

Every required training process participates in the Lightning checkpoint boundary. Only
the selected member retains the persistent continuation passed to Tune.

The Ray population runtime does not replace training-gradient communication, and the
training process group does not replace the Ray population-resolution boundary.

## Failure ownership

Each layer fails the facts it owns:

- the worker controller rejects invalid local lifecycle use;
- the selection policy rejects invalid comparison input;
- the Ray population runtime surfaces communication, membership, timeout, and generation
  isolation failures;
- Lightning surfaces checkpoint-construction failure; and
- the CBT Tune scheduler rejects incomplete or inconsistent generation transitions.

No layer may convert a failure into a valid partial-population winner.
