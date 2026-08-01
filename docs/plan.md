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

- a thin `ClanController` that stores one local fitness and resolves a cached
  checkpoint-source decision through an injected `exchange_fitness` callback;
- one deterministic selection function;
- `MutationSpec` for bounded linear or logarithmic mutation; and
- plain type aliases for scheduler-owned optimizer configurations.

There is no production Ray population runtime, Tune generation transition, Lightning
checkpoint integration, producer-provenance path, or repeated end-to-end Clan run.

## Current objective

Complete the first manually composable, directly qualified Clan Tuning integration while
preserving the ordinary Ray Tune and Lightning lifecycles.

## Work sequence

### 1. Ray population runtime

Replace the injected fitness callback with a Ray-owned population runtime implementing
the accepted all-gather decision. Preserve the controller's one-fitness, one-resolution,
cached-answer lifecycle and the explicit stable-member association.

Complete the focused tests and real multi-process qualification required by
[`qualification/ray_population_resolution.md`](qualification/ray_population_resolution.md).

### 2. Selected-checkpoint provenance

Identify and qualify the narrow Ray and Lightning seams through which only the selected
member retains and reports the training continuation. Add enough producer provenance for
Tune-side verification without introducing a second checkpoint payload or a second
configuration authority.

The exact metadata container and worker-facing helper are chosen in this work, not in the
architecture.

### 3. Tune generation transition

Use direct Ray evidence to choose between a scheduler specialization and another narrow
native adapter. Implement one authoritative complete-population transition that verifies
the selected continuation, applies the shared policy, derives target optimizer
configurations, assigns the common continuation, and releases the population together.

Do not restore the rejected persistent evolutionary-controller architecture.

### 4. Lightning/PyTorch training integration

Implement the narrow integration required for common distributed gradients,
member-local optimizer application, selected-member checkpoint persistence, and
restoration followed by target-configuration application.

Qualify the first supported optimizer, precision, device, and launch path rather than
claiming adjacent configurations by inference.

### 5. Repeated manual workflow

Complete a public manual composition through at least two generation transitions. The
run must expose the observable system behaviors in
[`contracts/system_behavior.md`](contracts/system_behavior.md), record its qualified
support boundary, and provide a reproducible mechanics example using the public package.

## Completion boundary

This plan is complete when the first supported manual integration repeatedly performs
Clan Tuning through the public path and its implementation, tests, qualification records,
documentation, and example agree. Easier assembly, broader optimizer layouts, additional
distributed modes, and operational extensions remain later work unless they are required
for that first claimed path.
