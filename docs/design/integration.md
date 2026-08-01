# Current integration design

Status: accepted design for the current implementation

## Purpose

This document translates the governing roadmap into the current system-level
lifecycle and responsibility boundaries. It does not repeat the Clan Tuning
method, define the population-resolution contract, choose a Ray collective
backend, or restate the public lowering documented in [`../api.md`](../api.md).

## Runtime model

One live Ray Tune trial represents one stable Clan member. The complete live
population participates in one distributed Lightning/PyTorch training job for a
round.

At the start of a round, every member restores the same selected model state,
optimizer history, and training progress. The optimizer configuration assigned
to that member is then applied without discarding the inherited optimizer state.

During training, PyTorch distributed execution produces the common gradient
required by Clan Tuning. Each member applies that gradient through its own
optimizer state and assigned configuration, producing the intended member
divergence.

At the round boundary, every member is evaluated at the same logical point on an
equivalent held-out workload. Fitness remains associated with the local member
until the Clan population boundary compares the complete population.

## Population decision before reporting

Before a worker reports to Tune, its thin `ClanController` participates once in
the Ray population-resolution path defined by the
[population invariants](../contracts/population_resolution_invariants.md) and
[responsibility contract](../contracts/population_resolution_responsibilities.md).

The Ray runtime returns complete member-associated fitness information. The
controller applies the shared framework-independent selection policy and caches
whether its local member is the sole checkpoint source. It does not own mutation,
future configurations, or the generation transition.

## Checkpoint and generation transition

Every process required by the Lightning checkpoint boundary participates in that
boundary. Only the selected member retains and reports the persistent training
continuation.

The selected worker binds its checkpoint to the stable member and assigned optimizer
configuration that produced it through the accepted public API. The exact provenance
representation and framework hook are implementation choices, not architectural
commitments.

The ClanBasedTuning Tune integration is authoritative over the complete
generation transition. It:

1. receives one valid result from every required member;
2. associates each result with the correct stable member and assigned optimizer
   configuration;
3. independently applies the same selection policy;
4. verifies that exactly the selected member supplied the continuation and that
   its provenance agrees;
5. derives the next optimizer configurations using the accepted
   framework-independent mutation policy;
6. assigns the selected continuation and one target configuration to every next
   member; and
7. releases the next population only after the complete transition is committed.

The Tune integration may be implemented through a scheduler specialization or
another narrow native adapter. This design fixes its authority and required
behavior, not that internal Ray seam.

## Responsibility boundaries

- **PyTorch distributed execution** owns ordinary gradient communication and
  distributed model mechanics.
- **Lightning** owns training-loop execution, validation timing, optimizer and
  training-state restoration, checkpoint construction, and its distributed
  barriers.
- **Ray Tune** owns trial execution, resources, scheduler lifecycle, and native
  checkpoint/configuration transfer.
- **The CBT Tune integration** owns Clan-specific population verification,
  selection authority, mutation, target configuration, and atomic generation
  release.
- **The Ray population runtime** owns the pre-report complete-population
  communication boundary, but not winner policy.
- **Framework-independent policy functions** own deterministic selection and
  mutation behavior without owning framework lifecycle.
- **`ClanController`** owns one worker's local fitness, one population decision,
  its cached local checkpoint-source answer, and winner-only producer provenance
  through the public API.
- **The assigned Tune configuration** is the live source of that member's
  optimizer configuration for the round.

No persistent evolutionary controller exists beside the Tune integration. No
package-owned Trainer, second training loop, second checkpoint payload, or
second winner-selection policy is introduced.

## Deliberately open implementation surface

The current design does not determine:

- scheduler subclass versus another narrow Tune adapter;
- the exact Lightning hooks used for checkpoint persistence and optimizer
  configuration application;
- additional factory arguments or advanced construction paths beyond the accepted
  public lowering;
- the checkpoint-provenance container or storage mechanism;
- Ray collective backend, payload device, dtype, or internal result type; or
- optimizer layouts beyond the first explicitly supported and qualified path.

Those choices may be made by the implementer only where they preserve the
roadmap, the public API, the system behavioral contract, and the
population-resolution contracts. Support claims remain limited to directly
qualified paths.
