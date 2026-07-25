# ClanBasedTuning project decisions

Status: accepted project decisions under Milestone 1 alignment review  
Date: 2026-07-24

## Purpose

This file records dated technical decisions that resolve choices left open by
the governing [product roadmap](../product_roadmap.md). Accepted decisions remain
authoritative unless a concrete roadmap, framework-evidence, or responsibility
conflict explicitly reopens them. A reopened decision remains under review until
a replacement is accepted.

This file does not contain milestone completion gates, audit history, temporary
support limits, or implementation plans. Those belong in the milestone,
research, evidence, and planning artifacts for their actual jobs.

## Current alignment status

- P1, P2, P5, and P6 remain accepted.
- P3 is reopened because the roadmap explicitly leaves the choice between a PBT
  specialization and a direct controller to Milestone 2.
- P4 is reopened because its earlier wording gave Ray the Clan-specific parent
  selection policy rather than only execution of the selected transition.
- P7 is reopened only for its milestone-specific recovery sentence. Its
  collective-validity and collective-completion rule remains accepted.

The revised P3, P4, and P7 text below is proposed for human acceptance. Until
then, the accepted portions named above continue to govern and the conflicting
clauses may not be used as implementation authority.

## P1. One Ray Tune trial represents one live Clan member

One Tune trial represents one Clan member. The complete population must be
concurrently resident, and every member participates in every shared training
gradient.

Ray remains the population authority. Later assembly work must make the
generated trial count, concurrent capacity, Clan world size, and dedicated
resources describe one consistent live population.

**Status:** accepted.

## P2. Lightning produces the evolutionary boundary

A Clan round ends at a qualifying Lightning validation-and-checkpoint event.
Lightning owns the training and validation cadence that produces the event; the
evolutionary controller consumes it rather than maintaining a second progress
clock.

The integration milestone must define which Lightning events qualify and prove
that all members reach them coherently.

**Status:** accepted.

## P3. Milestone 2 chooses the narrowest PBT-like controller form

The evolutionary subsystem owns the independently invokable Clan population
decision. Milestone 2 must choose, from direct framework evidence, whether that
policy is best implemented as a narrow specialization of an existing Ray PBT
scheduler or as a direct controller with the thinnest viable Ray adapter.

The selected design must preserve one Clan policy authority, independent
controller invocation, and native Ray ownership of ordinary trial execution,
checkpoint assignment, pause/resume, resource, and scheduler lifecycle behavior.
It must not reproduce substantial Tune controller machinery merely to avoid an
awkward or version-sensitive extension seam.

**Status:** reopened; revised text proposed. The previous fixed PBT-subclass
choice conflicts with the roadmap's explicit Milestone 2 design choice.

## P4. ClanBasedTuning selects the parent; Ray transfers state; Lightning restores it

ClanBasedTuning owns the Clan-specific population policy and therefore selects
the sole winning parent. In the Ray-backed path, Ray owns execution of the
resulting checkpoint and configuration assignment to target trials. Lightning
owns checkpoint contents and restoration.

After Lightning restores the parent's optimizer state, ClanBasedTuning reapplies
only the receiving member's evolved optimizer configuration. This division does
not create a separate Clan checkpoint scheduler, generation manifest, or
optimizer-construction system.

**Status:** reopened; revised text proposed. The previous wording incorrectly
assigned parent/source selection to Ray rather than the Clan policy.

## P5. Training data is partitioned; fitness data is comparable

Training retains normal distributed partitioning. Every member is evaluated on
the same held-out workload under comparable conditions, and each fitness value
remains local to its Tune trial until the population controller compares the
population.

The integration milestone owns the concrete sampler, metric, and reporting
contract.

**Status:** accepted.

## P6. Native PyTorch distributed execution owns shared-gradient mechanics

PyTorch's qualified distributed strategy owns ordinary model wrapping, gradient
bucketing, initial synchronization, and gradient collectives wherever its
qualified behavior fits. ClanBasedTuning may configure or narrowly specialize
the framework boundary, but it does not reimplement normal gradient reduction.

Milestone 3 must prove the first supported DDP path does not erase intended
member divergence. Later model-sharding support must preserve the same Clan
semantics through its native PyTorch/Lightning strategy rather than creating a
second distributed implementation.

**Status:** accepted core with scope clarification for the roadmap's later
model-sharding milestone.

## P7. Failure and planned completion are collective

Failure of one active member invalidates the active Clan. Planned completion
occurs only at a synchronized population boundary and ends the complete Clan.
No supported path may silently continue one member independently, shrink the
active population, or redefine a partial population as a valid Clan.

The controller must reject incomplete population input. The complete integration
must terminate or invalidate broken distributed execution clearly. Operational
interruption recovery becomes enforceable when the industry milestone defines
and qualifies its support envelope. These are applications of one collective
validity rule, not separate controller, integration, and production recovery
subsystems.

**Status:** collective rule accepted; revised milestone-allocation text proposed.

## Supporting record

The reasoning and source evidence behind these decisions and revisions are
recorded in:

- [Framework-alignment research report](../framework_alignment/research_report.md)
- [Framework-alignment evidence ledger](../framework_alignment/evidence_ledger.md)
- [Milestone 1 human review record](../framework_alignment/review_record.md)
