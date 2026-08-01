# Current integration design

Status: accepted design for the current implementation

## Purpose

This document defines the current system lifecycle, state authorities, and framework
boundaries. It does not repeat the Clan Tuning method, define the population-resolution
contract, choose a distributed backend, or restate the public lowering documented in
[`../api.md`](../api.md).

The design is firm about components and ordering that are required for one coherent Clan
Tuning system. It leaves framework hooks, internal representations, and replaceable
mechanisms open where they do not affect that system meaning.

## Runtime model

The supported integration keeps the ordinary Ray Tune function lifecycle. One live Tune
trial represents one stable Clan member. For the initial DDP path, that trial's training
process is one rank in the distributed group spanning the complete Clan.

The complete configured Clan is concurrently available before distributed initialization
and remains coherent across every shared training, population, checkpoint, and generation
boundary.

A CBT Tune scheduler is part of the integration and is the sole evolutionary authority.
Its exact Ray class hierarchy and scheduler hook path remain implementation choices; the
existence and authority of the scheduler do not.

The live optimizer configuration for one member is the controlled subset of that
member's scheduler-assigned Tune configuration. It is not an independent policy source.

The CBT worker integration supplies the stable member identity and cohort topology needed
by the externally launched Lightning process. Lightning and PyTorch use that information
to establish and tear down the distributed context. ClanBasedTuning does not create a
second process group for population resolution.

## Round boundary

A Clan round ends at a qualifying Lightning validation-and-checkpoint boundary.
Lightning owns the training and validation cadence that produces this boundary;
ClanBasedTuning consumes it rather than maintaining a second progress clock.

The exact Lightning hook or event combination that implements the qualifying boundary
remains subject to direct framework evidence. Every member must nevertheless reach the
same logical boundary before population comparison and transition.

## Shared training and member divergence

Native PyTorch DDP owns ordinary model synchronization and shared-gradient execution for
the supported initial path. Lightning owns the strategy lifecycle through which the
externally launched Tune trial processes join that DDP group.

At the beginning of a round, every member restores the same selected model state,
optimizer history, and training progress. The receiving member's scheduler-assigned
optimizer configuration is then applied without discarding inherited optimizer history.

During training, every member contributes its local training work to the common reduced
gradient. Each member applies that gradient through its own optimizer state and assigned
configuration, producing the intended divergence.

The integration must retain synchronization required to establish and reduce the common
training trajectory while preventing later parameter or persistent-buffer synchronization
from erasing member-local updates. The exact Tune-to-Lightning topology seam and DDP
options used to satisfy those requirements are implementation and qualification choices.
They do not transfer process-group ownership to ClanBasedTuning.

Training data remains normally partitioned. At the round boundary, every member is
evaluated under equivalent held-out conditions using the same metric definition.
Fitness remains associated with the local member rather than being reduced into one
shared Lightning metric.

## Population decision before reporting

Before a worker reports to Tune, its thin `ClanController` participates once in the
population-resolution boundary defined by the
[population invariants](../contracts/population_resolution_invariants.md) and
[responsibility contract](../contracts/population_resolution_responsibilities.md).

The population exchange uses the already-established framework-managed distributed
context spanning the Clan. It returns complete member-associated fitness information.
The controller applies the shared framework-independent selection policy and caches
whether its local member is the sole checkpoint source.

The controller and its population-resolution collaborator do not choose the distributed
backend, establish rendezvous, initialize or tear down a process group, own training
gradient communication, mutate future configurations, or advance the generation.

## Checkpoint and producer provenance

Every process required by the Lightning checkpoint boundary participates in that
boundary. Only the selected member retains and reports the persistent training
continuation.

Before reporting, the selected worker binds that checkpoint to:

- the stable member that produced it; and
- the exact controlled optimizer configuration used by that member for the round.

The accepted public API fixes the producer-provenance schema. This provenance is required
scheduler-verification data, not another configuration or evolution authority. The
framework metadata interface and checkpoint-storage mechanism used to persist that schema
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
policy, cohort coordination, and atomic transition; it does not replace those native
lifecycles.

## Responsibility boundaries

- **Ray Tune** owns trial execution, resource assignment, scheduler lifecycle, and native
  checkpoint/configuration transfer.
- **The CBT Tune scheduler** owns complete-Clan coordination, stable member assignment,
  population verification, winner authority, mutation, mutation random state, lineage,
  recovery state, target configurations, and atomic generation release.
- **The CBT worker integration** supplies the scheduler-assigned stable identity and
  cohort topology to the externally launched Lightning process without constructing the
  distributed group itself.
- **Lightning and PyTorch** own distributed initialization and teardown, backend and
  device behavior, training-loop execution, validation cadence, model synchronization,
  shared-gradient communication, collective execution, optimizer and training-state
  restoration, checkpoint construction, and distributed checkpoint barriers.
- **Framework-independent policy functions** own deterministic selection and mutation
  behavior without owning framework lifecycle.
- **`ClanController`** owns one worker's local fitness, one population decision over the
  established distributed context, its cached checkpoint-source answer, and winner-only
  producer provenance through the public API.
- **The controlled subset of the assigned Tune configuration** is the live source of
  that member's optimizer configuration for the round.

No persistent evolutionary controller exists beside the CBT Tune scheduler. The supported
integration introduces no package-owned Trainer, package-owned Trainable lifecycle,
process-group lifecycle, second training loop, second checkpoint payload, or second
winner-selection policy.

## Later model-sharded execution

The initial supported topology uses one distributed training process per Clan member.
A later ClanFSDP extension may need a composed topology that represents both model shards
and Clan members. That extension must preserve the same authority boundaries while
letting the framework own the resulting distributed groups. Its process mesh, group
layout, and FSDP hooks are deliberately not designed here.

## Deliberately open implementation surface

The current design does not determine:

- the CBT scheduler's exact Ray superclass, delegated native machinery, or hook methods;
- the exact Ray mechanism that admits the complete Clan together and exposes its topology;
- the exact Lightning cluster-environment or strategy seam that receives externally
  assigned rank, world-size, and rendezvous information;
- the exact Lightning hooks used for the qualifying round and checkpoint boundaries;
- the DDP options and collective operation used over the established distributed context;
- additional factory arguments or advanced construction paths beyond the accepted public
  lowering;
- the framework metadata interface or storage mechanism used for the accepted provenance
  schema;
- optimizer layouts beyond the first explicitly supported and qualified path; or
- the later ClanFSDP topology and framework seams.

Those choices may be made by the implementer only where they preserve the roadmap, the
public API, the system behavioral contract, and the population-resolution contracts.
Support claims remain limited to directly qualified paths.
