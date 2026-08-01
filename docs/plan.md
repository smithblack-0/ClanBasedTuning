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

There is no production Tune-trial-to-DDP topology integration, CBT Tune scheduler,
Lightning checkpoint integration, producer-provenance path, framework-managed population
exchange, or repeated end-to-end Clan run.

## Current objective

Complete the first manually composable, directly qualified Clan Tuning integration while
preserving the ordinary Ray Tune, Lightning, and PyTorch distributed lifecycles.

## Work sequence

### 1. Tune-member DDP cohort

Directly establish and qualify the initial topology in which one live Tune trial is one
stable Clan member and one rank in a native Lightning/PyTorch DDP group spanning the
complete Clan.

This work must resolve the smallest framework-native seams for:

- admitting the complete Clan with its required resources;
- assigning stable member and distributed-rank identity;
- supplying world-size and rendezvous facts to Lightning's externally launched process
  path;
- preventing independent trial lifecycle changes while the DDP cohort is active; and
- letting Lightning/PyTorch initialize and tear down the group.

Do not add package-owned GLOO, NCCL, CUDA, Ray collective, or PyTorch process-group
lifecycle. Complete the direct evidence required by
[`qualification/framework_managed_distributed_context.md`](qualification/framework_managed_distributed_context.md).

A minimal harness or narrow scheduler seam may be used to prove the topology. It must not
prematurely implement the full evolutionary transition or replace Tune's native trial and
resource ownership.

### 2. Population resolution over the established context

Replace the injected fitness callback with a narrow population exchange that uses the
already-established framework-managed distributed context.

Preserve the controller's one-fitness, one-resolution, cached-answer lifecycle and the
explicit association between stable members and gathered fitness. Qualify comparison
semantics, identity mapping, generation isolation, and incomplete-member failure without
creating another process group.

### 3. Selected-checkpoint provenance

Identify and qualify the narrow Ray Tune and Lightning seams through which only the
selected member retains and reports the training continuation. Implement the accepted
public producer-provenance behavior without introducing a second checkpoint payload or a
second configuration authority.

The stable member and exact controlled configuration are required provenance. The
accepted metadata schema is firm; the framework metadata and storage seam are selected by
direct evidence.

### 4. CBT Tune scheduler

Implement the accepted scheduler and its authoritative complete-population transition.
Use direct Ray evidence to choose its exact superclass, delegated native scheduler
machinery, persistence seam, cohort-admission integration, and hook path.

The scheduler verifies the selected continuation, applies the shared policy, derives one
target optimizer configuration per stable member, persists mutation and recovery state,
assigns the common continuation, and releases the population together.

Do not restore the rejected persistent evolutionary-controller architecture.

### 5. Complete Lightning/PyTorch training integration

Complete the narrow integration required for a Lightning-produced round boundary, native
DDP common gradients, member-local optimizer application, selected-member checkpoint
persistence, and restoration followed by target-configuration application.

Qualify the first supported optimizer, precision, device, and launch path rather than
claiming adjacent configurations by inference.

### 6. Repeated manual workflow

Complete a public manual composition through at least two generation transitions. The
run must expose the observable system behaviors in
[`contracts/system_behavior.md`](contracts/system_behavior.md), record its qualified
support boundary, and provide a reproducible mechanics example using the public package.

## Later ClanFSDP work

Model-sharded Clan execution is not part of the initial DDP completion path. Near the end
of the project, a separate ClanFSDP design and qualification effort may introduce a
composed topology that represents both model shards and Clan members while retaining
framework ownership of distributed groups.

The initial implementation must not pre-build that future topology or use it to justify a
second population communication system.

## Completion boundary

This plan is complete when the first supported manual integration repeatedly performs
Clan Tuning through the public path and its implementation, tests, qualification records,
documentation, and example agree. Easier assembly, broader optimizer layouts, ClanFSDP,
additional distributed modes, and operational extensions remain later work unless they
are required for that first claimed path.
