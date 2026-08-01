# ClanBasedTuning project decisions

Status: accepted project decisions  
Date: 2026-07-31

## Purpose

This file records dated technical decisions that resolve choices left open by the
governing [product roadmap](../product_roadmap.md). Accepted decisions remain
authoritative unless a concrete roadmap, framework-evidence, or responsibility conflict
explicitly reopens them. A reopened decision remains under review until a replacement
is accepted.

This file does not contain milestone completion gates, audit history, temporary support
limits, implementation plans, or qualification claims. Those belong in the milestone,
research, evidence, audit, design, planning, and qualification artifacts for their actual
jobs.

## Current alignment status

All seven decisions are accepted.

The Milestone 3 lifecycle separates four concerns:

- Ray collective population resolution among the live workers;
- framework-independent deterministic selection;
- winner-side producer-genome annotation;
- scheduler-owned mutation, lineage, recovery, and target assignment; and
- Lightning-owned training continuation.

The population-resolution design is divided by authority level:

- [population-resolution invariants](../design/population_resolution_invariants.md)
  state behavior every implementation must preserve; and
- [population-resolution responsibilities](../design/population_resolution_responsibilities.md)
  assign ownership where ambiguity could duplicate policy or lifecycle state.

Concrete Ray primitives, backends, devices, dtypes, transport containers, timeout values,
and qualification matrices are not project decisions unless later evidence shows that a
specific choice is required to preserve those contracts.

## P1. One Ray Tune trial represents one live Clan member

One Tune trial represents one Clan member. The complete population must be concurrently
resident, and every member participates in every shared training gradient and required
population boundary.

Ray remains the population runtime authority. Later assembly work must make the
generated trial count, concurrent capacity, Clan world size, and dedicated resources
describe one consistent live population.

**Status:** accepted.

## P2. Lightning produces the evolutionary boundary

A Clan round ends at a qualifying Lightning validation-and-checkpoint event. Lightning
owns the training and validation cadence that produces the event; CBT consumes it
rather than maintaining a second progress clock.

The integration milestone must define which Lightning events qualify and prove that all
members reach them coherently.

**Status:** accepted.

## P3. The Tune scheduler is the sole evolutionary policy authority

The CBT Tune scheduler owns the complete population policy transition:

- associate fitness with active member genomes;
- select and verify the winning parent;
- derive child optimizer-hyperparameter configurations;
- own mutation random state;
- persist recovery and replay lineage;
- install target trial configurations; and
- coordinate selected-checkpoint assignment.

Framework-independent selection and mutation primitives remain independently testable
without Ray trial objects. Their independence does not make the worker controller, Ray
population runtime, or a second policy object authoritative over evolution.

The worker path has a narrower responsibility. A Ray collective population runtime
returns complete member-associated fitness information. `ClanController` applies the
shared deterministic selection policy, caches whether its local member is the checkpoint
source, and later allows only that selected worker to attach its copied current genome to
the checkpoint.

The controller does not derive future configurations, advance generations, or persist
scheduler lineage. The Ray runtime transports population information but does not own
winner-selection policy.

**Status:** accepted; revised on 2026-07-31 after the persistent evolutionary-controller
shape was replaced by the thin worker lifecycle.

## P4. CBT selects and mutates; Ray transfers state; Lightning restores it

ClanBasedTuning owns the Clan-specific population policy through its Tune scheduler and
therefore selects the sole winning parent and derives the next population genomes.

Ray owns execution of the resulting checkpoint and configuration assignment to target
trials. Lightning owns checkpoint payload construction, contents, and restoration.

After Lightning restores the parent's optimizer state, CBT reapplies only the receiving
member's scheduler-assigned optimizer configuration. This division does not create a
second checkpoint format, generation manifest, or optimizer-construction system.

The selected worker annotates the checkpoint before reporting it with the stable member
ID and copied genome that produced the payload. That metadata is provenance used by the
scheduler for verification; it is not a second mutation or child-genome authority.

**Status:** accepted; revised on 2026-07-31 to place producer annotation before
checkpoint publication while retaining scheduler policy authority.

## P5. Training data is partitioned; fitness data is comparable

Training retains normal distributed partitioning. Every member is evaluated on the same
held-out workload under comparable conditions, and each fitness value remains local to
its Tune trial until the active population reaches the CBT comparison boundary.

At that boundary, Ray collective communication produces a complete association between
every required stable member and exactly one valid local fitness. Every worker applies
the same framework-independent comparison and tie policy so exactly one member knows it
may retain and report the checkpoint.

The Tune scheduler independently applies that shared policy to the complete reported
generation and verifies that the checkpoint source agrees.

The integration milestone owns the concrete sampler, metric, communication mechanism,
identity mapping, failure release, and reporting evidence, subject to the accepted
population-resolution invariants and responsibilities.

**Status:** accepted; comparison ownership clarified on 2026-07-31 so the pre-report
worker decision and scheduler policy verification cannot drift.

## P6. Native PyTorch DDP owns shared-gradient execution

PyTorch DDP owns ordinary model wrapping, gradient bucketing, initial synchronization,
and gradient collectives wherever its qualified behavior fits. ClanBasedTuning may
configure or narrowly specialize the framework boundary, but it does not reimplement
normal all-reduce.

Ray collective communication owns the separate Clan-level population-resolution
boundary. This responsibility separation does not require a particular Ray backend,
device placement, dtype, or collective primitive.

The integration milestone must prove that native synchronization does not erase
intended member divergence.

**Status:** accepted unchanged. Later model-sharding support is introduced and qualified
by the roadmap's industry milestone rather than by rewriting this DDP contract in
advance.

## P7. Failure and planned completion are collective

Failure of one active member invalidates the active Clan. Planned completion occurs only
at a synchronized population boundary and ends the complete Clan. No supported path may
silently continue one member independently, shrink the active population, or redefine a
partial population as a valid Clan.

Population-resolution failure must release waiting participants through a surfaced
failure and must not produce a checkpoint source from missing, duplicated, malformed, or
cross-generation participation.

Detailed timeout values, cancellation mechanics, exception types, diagnosis, scheduler
recovery, and operational behavior belong in implementation and support contracts where
those capabilities become enforceable.

**Status:** accepted; the collective validity rule is unchanged.

## Supporting record

The reasoning and source evidence behind these decisions and revisions are recorded in:

- [Framework-alignment research report](../framework_alignment/research_report.md)
- [Framework-alignment evidence ledger](../framework_alignment/evidence_ledger.md)
- [Milestone 1 acceptance record](../framework_alignment/review_record.md)
- [Framework-alignment review audit](../framework_alignment/review_audit.md)
- [Milestone 3 system architecture](../design/system_architecture.md)
- [Population-resolution invariants](../design/population_resolution_invariants.md)
- [Population-resolution responsibilities](../design/population_resolution_responsibilities.md)
- [Milestone 3 behavioral contracts](../design/behavioral_test_contracts.md)
