# Active implementation plan

Status: current implementation sequence

## Authority

This plan sequences the present work. It does not change the
[roadmap](product_roadmap.md), the [integration design](design/integration.md), or
the [behavioral](contracts/system_behavior.md) and
[population-resolution](contracts/population_resolution_invariants.md) contracts.
Implementation evidence may change the sequence or an internal choice without changing
those authorities.

## Current baseline

The package currently contains:

- a thin `ClanController` that stores one local fitness, consumes complete
  member-associated fitness from a population runtime, and caches one local
  checkpoint-source decision;
- an internal Ray GLOO population runtime with explicit member-to-rank association,
  CPU `float64` all-gather, persistent group lifecycle, and actor exit on an operation
  timeout;
- one deterministic selection function;
- `MutationSpec` for bounded linear or logarithmic mutation; and
- plain type aliases for scheduler-owned optimizer configurations.

The internal CPU/GLOO component has real multi-actor evidence for identity, precision,
repeated boundaries, cached decisions, and omitted-participant failure. It is not yet
wired through the accepted public factory or a Tune training function.

There is no producer-provenance path, CBT Tune scheduler, Lightning checkpoint
integration, optimizer-configuration application, or repeated end-to-end Clan run.

## Current objective

Complete the first manually composable, directly qualified Clan Tuning integration while
preserving the ordinary Ray Tune and Lightning lifecycles.

## Work sequence

### 1. Ray population runtime

The initial internal runtime is implemented and qualified for the retained CPU/GLOO actor
path. It preserves the controller's one-fitness, one-resolution, cached-answer lifecycle
and translates collective rank through explicit stable-member association.

Further evidence remains cumulative as later slices add public worker construction,
checkpoint suppression, scheduler transition, and complete failure propagation. CUDA or
other transport paths are not part of the current claim.

### 2. Selected-checkpoint provenance

Implement the accepted controller lowering:

- copy the current controlled optimizer configuration into the worker controller;
- permit only a resolved selected controller to call `save_genome(checkpoint)`;
- write the accepted `{schema_version, member_id, genome}` provenance schema;
- preserve the same checkpoint reference and leave the Lightning payload unchanged; and
- prevent publication when provenance cannot be attached.

Identify and qualify the narrow Ray checkpoint metadata interface and Lightning ordering
needed to satisfy that public behavior. The schema and public controller method are firm;
the framework storage mechanism and hook are chosen in this work.

### 3. CBT Tune scheduler

Implement the accepted scheduler and its authoritative complete-population transition.
Use direct Ray evidence to choose its exact superclass, delegated native scheduler
machinery, persistence seam, and hook path.

The scheduler verifies the selected continuation, applies the shared policy, derives one
target optimizer configuration per stable member, persists mutation and recovery state,
assigns the common continuation, and releases the population together.

Do not restore the rejected persistent evolutionary-controller architecture.

### 4. Lightning/PyTorch training integration

Implement the narrow integration required for a Lightning-produced round boundary,
native DDP common gradients, member-local optimizer application, selected-member
checkpoint persistence, and restoration followed by target-configuration application.

Qualify the first supported optimizer, precision, device, and launch path rather than
claiming adjacent configurations by inference.

### 5. Public worker construction and repeated manual workflow

Implement `make_cbt_controller(genome=...)` so the ordinary Tune function does not
manually construct collective groups, identities, transport collaborators, or comparison
policy. Compose the accepted runtime, controller, scheduler, and Lightning/PyTorch path
through at least two generation transitions.

The run must expose the observable system behaviors in
[`contracts/system_behavior.md`](contracts/system_behavior.md), record its qualified
support boundary, and provide a reproducible mechanics example using the public package.

## Completion boundary

This plan is complete when the first supported manual integration repeatedly performs
Clan Tuning through the public path and its implementation, tests, qualification records,
documentation, and example agree. Easier assembly, broader optimizer layouts, additional
distributed modes, and operational extensions remain later work unless required for that
first claimed path.
