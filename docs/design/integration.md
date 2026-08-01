# Current integration design

Status: accepted design for the current implementation

## Purpose

This document defines the current system lifecycle, state authorities, and framework
boundaries. It does not repeat the Clan Tuning method, define the population-resolution
contract, choose a Ray collective backend, or restate the public lowering documented in
[`../api.md`](../api.md).

The design is firm about components and ordering that are required for one coherent Clan
Tuning system. It leaves framework hooks, internal representations, and replaceable
mechanisms open where they do not affect that system meaning.

## Runtime model

The supported integration keeps the ordinary Ray Tune function lifecycle. One live Tune
trial represents one stable Clan member, and the complete configured Clan is concurrently
available for every shared training and population boundary.

A CBT Tune scheduler is part of the integration and is the sole evolutionary authority.
Its exact Ray class hierarchy and scheduler hook path remain implementation choices; the
existence and authority of the scheduler do not.

The live optimizer configuration for one member is the controlled subset of that
member's scheduler-assigned Tune configuration. It is not an independent policy source.

## Round boundary

A Clan round ends at a qualifying Lightning validation-and-checkpoint boundary.
Lightning owns the training and validation cadence that produces this boundary;
ClanBasedTuning consumes it rather than maintaining a second progress clock.

The exact Lightning hook or event combination that implements the qualifying boundary
remains subject to direct framework evidence. Every member must nevertheless reach the
same logical boundary before population comparison and transition.

## Shared training and member divergence

Native PyTorch DDP owns ordinary model synchronization and shared-gradient execution for
the supported initial path.

At the beginning of a round, every member restores the same selected model state,
optimizer history, and training progress. The receiving member's scheduler-assigned
optimizer configuration is then applied without discarding inherited optimizer history.

During training, every member contributes its local training work to the common reduced
gradient. Each member applies that gradient through its own optimizer state and assigned
configuration, producing the intended divergence.

The integration must retain synchronization required to establish and reduce the common
training trajectory while preventing later parameter or persistent-buffer synchronization
from erasing member-local updates. The exact DDP options used to satisfy that requirement
are implementation and qualification choices.

Training data remains normally partitioned. At the round boundary, every member is
evaluated under equivalent held-out conditions using the same metric definition.
Fitness remains associated with the local member rather than being reduced into one
shared Lightning metric.

## Population decision before reporting

Before a worker reports to Tune, its thin `ClanController` participates once in the Ray
population-resolution path defined by the
[population invariants](../contracts/population_resolution_invariants.md) and
[responsibility contract](../contracts/population_resolution_responsibilities.md).

The Ray runtime returns complete member-associated fitness information. The controller
applies the shared framework-independent selection policy and caches whether its local
member is the sole checkpoint source. It does not own mutation, future configurations,
or the generation transition.

## Checkpoint and producer provenance

Every process required by the Lightning checkpoint boundary participates in that
boundary. Only the selected member retains and reports the persistent training
continuation.

Before reporting, the selected worker binds that checkpoint to:

- the stable member that produced it; and
- the exact controlled optimizer configuration used by that member for the round.

This provenance is required scheduler-verification data, not another configuration or
evolution authority. The exact metadata keys, container, and checkpoint-storage mechanism
remain implementation choices. The worker must not publish the checkpoint if provenance
attachment fails.

The controller does not write child configurations, mutation state, scheduler lineage,
recovery state, or other Tune-owned transition data.

## Scheduler-owned generation transition

The CBT Tune scheduler closes the complete generation. It:

1. receives one valid result from every required member;
2. associates each result with the correct stable member and active controlled
   configuration;
3. independently applies the same deterministic selection policy used by workers;
4. verifies that exactly the selected member supplied the continuation and that its
   producer provenance agrees;
5. derives one next optimizer configuration for every stable target member;
6. advances and persists the mutation random state, lineage, and recovery state needed
   to reproduce or restore the accepted transition;
7. assigns the same selected continuation and one target configuration to every next
   member; and
8. releases the complete next population only after the transition is durably accepted.

A crash before that transition is accepted must recover the previous completed generation
or fail the experiment. It must not release a population containing mixed checkpoints,
configurations, lineage, or generation state.

Ray Tune continues to own native trial execution, resources, scheduler lifecycle, and
checkpoint/configuration transfer. The CBT scheduler adds the Clan-specific population
policy and atomic transition; it does not replace those native lifecycles.

## Responsibility boundaries

- **PyTorch DDP** owns ordinary model synchronization and shared-gradient execution.
- **Lightning** owns training-loop execution, validation cadence, optimizer and
  training-state restoration, checkpoint construction, and distributed checkpoint
  barriers.
- **Ray Tune** owns trial execution, resources, scheduler lifecycle, and native
  checkpoint/configuration transfer.
- **The CBT Tune scheduler** owns population verification, winner authority, mutation,
  mutation random state, lineage, recovery state, target configurations, and atomic
  generation release.
- **The Ray population runtime** owns the pre-report complete-population communication
  boundary, but not winner policy.
- **Framework-independent policy functions** own deterministic selection and mutation
  behavior without owning framework lifecycle.
- **`ClanController`** owns one worker's local fitness, one population decision, its
  cached checkpoint-source answer, and winner-only producer provenance through the
  public API.
- **The controlled subset of the assigned Tune configuration** is the live source of
  that member's optimizer configuration for the round.

No persistent evolutionary controller exists beside the CBT Tune scheduler. The supported
integration introduces no package-owned Trainer, package-owned Trainable lifecycle,
second training loop, second checkpoint payload, or second winner-selection policy.

## Deliberately open implementation surface

The current design does not determine:

- the CBT scheduler's exact Ray superclass, delegated native machinery, or hook methods;
- the exact Lightning hooks used for the qualifying round and checkpoint boundaries;
- additional factory arguments or advanced construction paths beyond the accepted public
  lowering;
- the checkpoint-provenance keys, container, or storage mechanism;
- Ray collective backend, payload device, dtype, or internal result type; or
- optimizer layouts beyond the first explicitly supported and qualified path.

Those choices may be made by the implementer only where they preserve the roadmap, the
public API, the system behavioral contract, and the population-resolution contracts.
Support claims remain limited to directly qualified paths.
