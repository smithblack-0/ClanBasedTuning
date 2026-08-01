# Population-resolution responsibilities

Status: accepted architectural contract

## Purpose

This document assigns ownership for satisfying the
[population-resolution invariants](population_resolution_invariants.md).

It fixes authority boundaries where ambiguity could duplicate policy or hide lifecycle
state. It deliberately does not freeze internal fitness representation, collective
operation, helper names, or framework hooks that do not affect those boundaries.

## Semantic boundary

The population-resolution operation accepts one member's local fitness at one generation
boundary and returns a complete association between stable Clan members and their fitness
values.

That association is the contract. Its concrete Python type is not architectural.

A successful result contains exactly one finite comparable fitness for every required
stable member. The mapping between distributed participation and stable member identity
is explicit or mechanically proven; incidental sequence position is insufficient unless
its meaning is established by the integration contract.

The population-resolution operation does not own the distributed context through which
that association is produced.

## Complete-Clan topology

The CBT Tune scheduler owns the configured Clan as a cohort. It determines which live
Tune trial represents each stable member and ensures the complete required cohort is
available for shared distributed execution.

The worker integration conveys the scheduler-assigned stable member identity and the
cohort topology required by Lightning's externally launched process model. This includes
the semantic facts needed to establish rank, world size, and rendezvous, but does not make
ClanBasedTuning the owner of distributed initialization.

The exact Ray scheduling and placement mechanism and the exact Lightning environment seam
remain implementation decisions requiring direct framework evidence.

## Framework-managed distributed context

Lightning, PyTorch, and the external trial process lifecycle own:

- process-group initialization and lifetime;
- backend and device behavior;
- rank and world-size realization from the supplied topology;
- training-gradient communication;
- barriers and collective execution;
- release through the qualified strategy or trial-process lifecycle; and
- propagation of distributed failures through the supported framework lifecycle.

For the initial DDP path, the already-established training group also carries the
population fitness exchange. Population-resolution code does not create, configure,
rendezvous, time out, or release a second Ray, GLOO, NCCL, CUDA, or PyTorch process group.

A later ClanFSDP extension may require a composed topology with multiple framework-owned
groups. That does not transfer group lifecycle into the controller or selection logic.

## Population exchange

The narrow population-exchange collaborator owns:

- contributing one local fitness through the established Clan-wide distributed context;
- returning complete fitness associated with stable member identity;
- preventing values from different generation boundaries from being accepted together;
  and
- rejecting malformed, incomplete, or ambiguously associated results.

It does not own:

- process-group lifecycle or backend choice;
- minimizing or maximizing policy;
- tie-breaking policy;
- winner selection;
- mutation or child-configuration derivation;
- scheduler lineage or recovery;
- checkpoint construction; or
- Tune result reporting.

Its exact collaborator interface, collective primitive, payload representation, and
container type remain internal implementation choices.

## Framework-independent selection policy

The shared selection policy owns:

- comparison direction;
- comparison-validity rules;
- stable deterministic tie behavior; and
- selection of one stable member from complete member-associated fitness.

The worker-side path and CBT Tune scheduler use the same implementation. The population
exchange does not contain a second winner-selection rule.

## Worker controller

`ClanController` owns the worker-facing state and ordering:

- the stable identity of its local member;
- comparison mode;
- one local fitness value;
- one invocation of the population exchange;
- application of the shared selection policy to the complete result;
- one cached local save decision; and
- copied current-configuration provenance and winner-only provenance writing.

The controller does not create or release distributed groups. It does not expose ranks,
rendezvous details, or transport buffers to the user training function. It does not
mutate configurations, derive child configurations, advance generations, or persist Tune
transition state.

The accepted public methods and ordinary construction flow are defined in
[`../api.md`](../api.md). This contract does not fix the controller's internal
collaborator interface or concrete population-result type.

## Worker integration

The worker integration implements the accepted `make_cbt_controller(genome=...)` flow.
It obtains stable member identity, population membership, comparison configuration,
generation context, and access to the established framework population exchange without
requiring the user training function to assemble those details manually.

The same integration supplies the scheduler-assigned distributed topology to Lightning
through a supported externally launched process seam. It does not call distributed
initialization, release the process group, or choose the backend itself.

Additional factory arguments, advanced construction paths, and internal wiring remain
open. The ordinary path and its responsibility do not: hide framework wiring while
preserving ordinary Tune, Lightning, and PyTorch lifecycles.

## CBT Tune scheduler

A CBT Tune scheduler exists and owns the authoritative generation transition. It:

- coordinates one complete live Clan;
- assigns stable member identity and target optimizer configuration;
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

The scheduler's exact Ray superclass, cohort-admission mechanism, delegated native
scheduler machinery, persistence seam, and hook methods remain open to direct framework
evidence.

## Lightning and PyTorch

Lightning owns training-loop cadence, the qualifying validation-and-checkpoint boundary,
checkpoint construction, restoration, and the distributed strategy lifecycle. Native
PyTorch DDP owns shared-gradient communication for the supported initial path. Ray Tune
owns the externally launched trial process whose termination may release the process group
for that qualified path.

Every required training process participates in the Lightning checkpoint boundary. Only
the selected member retains the persistent continuation passed to Tune.

The established distributed training context also supports the population exchange; the
exchange is a different semantic operation, not a separately owned communication system.

## Failure ownership

Each layer fails the facts it owns:

- the worker controller rejects invalid local lifecycle use;
- the selection policy rejects invalid comparison input;
- the population exchange rejects malformed, incomplete, or ambiguously associated
  population results;
- Lightning, PyTorch, and the trial process lifecycle surface distributed initialization,
  communication, member failure, and cleanup;
- Lightning surfaces checkpoint-construction failure; and
- the CBT Tune scheduler rejects incomplete or inconsistent cohort and generation
  transitions.

No layer may convert a failure into a valid partial-population winner.
