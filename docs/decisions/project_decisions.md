# ClanBasedTuning project decisions

Status: accepted project decisions  
Date: 2026-07-31

## Purpose

This file records technical decisions that resolve choices left open by the governing
[product roadmap](../product_roadmap.md). Accepted decisions remain authoritative unless
a concrete roadmap, framework-evidence, or responsibility conflict explicitly reopens
them.

Milestone gates define completion evidence. Design documents refine implementation
requirements without silently replacing these decisions.

## Current alignment status

All seven decisions remain accepted.

The Milestone 3 lifecycle separates:

- a Ray collective used by the live workers to identify one pre-report checkpoint
  source;
- winner-side producer-genome annotation;
- scheduler-owned evolution, lineage, recovery, and target assignment; and
- Lightning-owned training and checkpoint continuation.

The Ray-collective commitment is accepted. The exact collective primitive, exchanged
result shape, member/rank representation, controller collaborator boundary, and final
names remain implementation-design questions. See
[Ray population-resolution design](../design/population_resolution.md).

## P1. One Ray Tune trial represents one live Clan member

One Tune trial represents one stable Clan member. The complete population is
concurrently resident, and every member participates in every shared training gradient
and every required population boundary.

Ray remains the population runtime authority. Trial count, concurrent capacity, Clan
world size, and dedicated resources must describe one consistent live population.

**Status:** accepted.

## P2. Lightning produces the evolutionary boundary

A Clan round ends at a qualifying Lightning validation-and-checkpoint event. Lightning
owns the training and validation cadence that produces the event; CBT consumes it
rather than maintaining a second progress clock.

The integration milestone must define which Lightning events qualify and prove that all
members reach them coherently.

**Status:** accepted.

## P3. The Tune scheduler is the sole evolutionary policy authority

The CBT Tune scheduler owns the complete population-policy transition:

- associate fitness with active member genomes;
- select and verify the winning parent;
- derive child optimizer-hyperparameter configurations;
- own mutation random state;
- persist recovery and replay lineage;
- install target trial configurations; and
- coordinate selected-checkpoint assignment.

Framework-independent selection and mutation primitives remain independently testable.
Their independence does not make the worker controller or the Ray collective runtime an
evolutionary authority.

The worker-side path has a narrower responsibility: before Tune reporting, the complete
live population uses a Ray collective to identify exactly one stable checkpoint source.
The local decision is cached so later provenance checks do not repeat the collective.

The exact worker/controller/runtime interface is not fixed by this decision.

**Status:** accepted.

## P4. CBT selects and mutates; Ray transfers state; Lightning restores it

ClanBasedTuning owns the Clan-specific population policy through its Tune scheduler and
therefore selects the winning parent and derives the next population genomes.

Ray owns execution of checkpoint and configuration assignment to target trials.
Lightning owns checkpoint payload construction, contents, and restoration.

After Lightning restores the parent's optimizer state, CBT reapplies only the receiving
member's scheduler-assigned optimizer configuration. This division creates neither a
second checkpoint format nor a package-owned training loop.

The selected worker annotates its completed checkpoint before reporting it with the
stable member ID and copied genome that produced the payload. That metadata is
provenance for scheduler verification, not a child-genome authority.

**Status:** accepted.

## P5. Training data is partitioned; fitness data is comparable

Training retains normal distributed partitioning. Every member is evaluated on the same
held-out workload under comparable conditions, and each fitness value remains local to
its Tune trial until the population reaches the comparison boundary.

Before checkpoint reporting, every required member participates in one Ray collective
population-resolution operation. The successful operation associates one valid fitness
with every stable member and yields one deterministic selected member under the shared
comparison and tie policy.

The Tune scheduler independently applies the same selection policy to the complete Tune
results and verifies that the checkpoint source agrees.

The integration milestone owns the exact Ray primitive, stable identity mapping,
generation isolation, timeout, failure release, and worker-facing interface.

**Status:** accepted.

## P6. Native PyTorch DDP owns shared-gradient execution

PyTorch DDP owns ordinary model wrapping, gradient bucketing, initial synchronization,
and gradient collectives wherever its qualified behavior fits. ClanBasedTuning may
configure or narrowly specialize the framework boundary, but it does not reimplement
normal all-reduce.

The Ray population collective is a separate Clan-level coordination boundary. It must
not be replaced with the DDP process group merely because both mechanisms communicate
between the same live processes.

The integration milestone must prove that native synchronization does not erase
intended member divergence.

**Status:** accepted.

## P7. Failure and planned completion are population-wide

Failure of one active member invalidates the active Clan. Planned completion occurs only
at a synchronized population boundary and ends the complete Clan. No supported path may
silently continue one member independently, shrink the active population, or redefine a
partial population as valid.

For Ray population resolution, a missing, duplicated, malformed, or cross-generation
participant must fail or time out the boundary and release waiting work through a
surfaced error. It must not produce a winner from a partial population.

**Status:** accepted.

## Supporting record

The reasoning and evidence behind these decisions are recorded in:

- [Framework-alignment research report](../framework_alignment/research_report.md)
- [Framework-alignment evidence ledger](../framework_alignment/evidence_ledger.md)
- [Milestone 1 acceptance record](../framework_alignment/review_record.md)
- [Framework-alignment review audit](../framework_alignment/review_audit.md)
- [Milestone 3 system architecture](../design/system_architecture.md)
- [Ray population-resolution design](../design/population_resolution.md)
- [Milestone 3 behavioral contracts](../design/behavioral_test_contracts.md)
