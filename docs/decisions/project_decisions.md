# ClanBasedTuning project decisions

Status: accepted project decisions  
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

All seven decisions are accepted. P3, P4, and the allocation portion of P7 were
revised during the Milestone 1 alignment pass and accepted by human review on
2026-07-24. P3 was clarified again when Milestone 2 began: the independent
controller belongs to Milestone 2, while selection and implementation of its Ray
invocation seam belong to Milestone 3. P1, P2, P5, and P6 retained their accepted
authority throughout these corrections.

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

## P3. Milestone 2 owns the controller; Milestone 3 owns Ray integration

Milestone 2 delivers an independently invokable Clan population controller. The
controller consumes one complete population result, selects the sole parent, and
produces one complete next-generation optimizer-configuration decision without
owning live trials, checkpoints, training, or framework lifecycle execution.

Its public contract must be designed for its immediate Ray Tune consumer: stable
member identities, ordinary fitness values and configuration mappings, explicit
policy state, and one complete decision that a later integration layer can carry
without inventing a second experiment schema. Ray objects and adapter lifecycle
do not become part of the controller merely to anticipate that consumer.

Milestone 3 chooses and implements the narrowest justified Ray invocation seam.
That work must preserve one Clan policy authority and native Ray ownership of
ordinary trial execution, checkpoint assignment, pause/resume, resources, and
scheduler lifecycle behavior. It must not reproduce substantial Tune controller
machinery merely to avoid an awkward or version-sensitive extension seam.

**Status:** accepted. This replaces the earlier assignment of the
PBT-specialization-versus-adapter choice to Milestone 2.

## P4. ClanBasedTuning selects the parent; Ray transfers state; Lightning restores it

ClanBasedTuning owns the Clan-specific population policy and therefore selects
the sole winning parent. In the Ray-backed path, Ray owns execution of the
resulting checkpoint and configuration assignment to target trials. Lightning
owns checkpoint contents and restoration.

After Lightning restores the parent's optimizer state, ClanBasedTuning reapplies
only the receiving member's evolved optimizer configuration. This division does
not create a separate Clan checkpoint scheduler, generation manifest, or
optimizer-construction system.

**Status:** accepted; revised during Milestone 1 alignment because the previous
wording incorrectly assigned parent/source selection to Ray rather than the Clan
policy.

## P5. Training data is partitioned; fitness data is comparable

Training retains normal distributed partitioning. Every member is evaluated on
the same held-out workload under comparable conditions, and each fitness value
remains local to its Tune trial until the population controller compares the
population.

The integration milestone owns the concrete sampler, metric, and reporting
contract.

**Status:** accepted. The comparison-owner wording is aligned with P3 and P4;
the accepted data and fitness semantics are unchanged.

## P6. Native PyTorch DDP owns shared-gradient execution

PyTorch DDP owns ordinary model wrapping, gradient bucketing, initial
synchronization, and gradient collectives wherever its qualified behavior fits.
ClanBasedTuning may configure or narrowly specialize the framework boundary, but
it does not reimplement normal all-reduce.

The integration milestone must prove that native synchronization does not erase
intended member divergence.

**Status:** accepted unchanged. Later model-sharding support is introduced and
qualified by the roadmap's industry milestone rather than by rewriting this DDP
contract in advance.

## P7. Failure and planned completion are collective

Failure of one active member invalidates the active Clan. Planned completion
occurs only at a synchronized population boundary and ends the complete Clan.
No supported path may silently continue one member independently, shrink the
active population, or redefine a partial population as a valid Clan.

Detailed termination, invalidation, diagnosis, and operational recovery behavior
belongs in the integration and support contracts where those capabilities become
enforceable. This decision states the collective validity rule; it does not
create separate recovery subsystems or assign their detailed qualification.

**Status:** accepted; the milestone-specific recovery allocation was removed
during Milestone 1 alignment while the collective rule remained unchanged.

## Supporting record

The reasoning and source evidence behind these decisions and revisions are
recorded in:

- [Framework-alignment research report](../framework_alignment/research_report.md)
- [Framework-alignment evidence ledger](../framework_alignment/evidence_ledger.md)
- [Milestone 1 human review record](../framework_alignment/review_record.md)
