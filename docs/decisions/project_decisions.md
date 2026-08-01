# ClanBasedTuning project decisions

Status: accepted project decisions  
Date: 2026-07-31  
Population-resolution clarification: 2026-08-01

## Purpose

This file records technical decisions that resolve choices left open by the governing
[product roadmap](../product_roadmap.md). Accepted decisions remain authoritative unless
a concrete roadmap, framework-evidence, or responsibility conflict explicitly reopens
them.

This file does not define milestone completion evidence, temporary support limits, or
implementation plans. Those belong in their corresponding artifacts.

## Current alignment status

All seven decisions remain accepted.

The high-level Milestone 3 lifecycle is accepted:

- one Tune trial represents one live Clan member;
- Lightning and PyTorch own distributed training and checkpoint construction;
- the CBT Tune scheduler owns evolutionary policy and next-generation assignment;
- exactly one completed member supplies the continuation checkpoint; and
- the selected worker records the genome that produced that checkpoint before reporting
  it.

The mechanism that lets workers determine the sole checkpoint source before reporting
is **not yet accepted**. No existing callback name, all-gather implementation, Ray
collective, PyTorch collective, rank mapping, timeout policy, or module layout is
promoted by these decisions. That seam must be designed and qualified in the current
iteration.

## P1. One Ray Tune trial represents one live Clan member

One Tune trial represents one Clan member. The complete population must be concurrently
resident, and every member participates in every shared training gradient.

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

The CBT Tune scheduler owns the complete population policy transition:

- associate fitness with active member genomes;
- select and verify the winning parent;
- derive child optimizer-hyperparameter configurations;
- own mutation random state;
- persist recovery and replay lineage;
- install target trial configurations; and
- coordinate selected-checkpoint assignment.

Framework-independent selection and mutation primitives remain independently testable.
Their independence does not make the worker controller or another policy object
authoritative over evolution.

The worker controller has a narrower purpose. It holds worker-local boundary state,
obtains the local answer to the pre-report checkpoint-source decision, caches that
answer, and allows only the selected worker to attach producer-genome metadata.

How the complete population reaches that decision is an integration responsibility that
remains open. The controller does not choose a communication backend or own future
configurations, generation advancement, or scheduler lineage.

**Status:** accepted; population-resolution mechanism reopened on 2026-08-01.

## P4. CBT selects and mutates; Ray transfers state; Lightning restores it

ClanBasedTuning owns the Clan-specific population policy through its Tune scheduler and
therefore selects the sole winning parent and derives the next population genomes.

Ray owns execution of checkpoint and configuration assignment to target trials.
Lightning owns checkpoint payload construction, contents, and restoration.

After Lightning restores the parent's optimizer state, CBT reapplies only the receiving
member's scheduler-assigned optimizer configuration. This division creates neither a
second checkpoint format nor a package-owned training loop.

The selected worker annotates the checkpoint before reporting it with the stable member
ID and copied genome snapshot that produced the payload. That metadata is provenance
for scheduler verification; it is not a second mutation or child-genome authority.

**Status:** accepted.

## P5. Training data is partitioned; fitness data is comparable

Training retains normal distributed partitioning. Every member is evaluated on the same
held-out workload under comparable conditions, and each fitness value remains local to
its Tune trial until the population reaches the comparison boundary.

Before checkpoint reporting, the complete active population must produce one consistent
checkpoint-source result. The Tune scheduler independently applies the same accepted
comparison rule to the complete reported generation and verifies that the checkpoint
source agrees.

The integration milestone owns the sampler, metric, synchronization, membership,
ordering, failure, and reporting contracts. It must choose those mechanisms from current
framework evidence rather than inherit an earlier collective implementation.

**Status:** accepted; transport and callback shape remain unresolved.

## P6. Native PyTorch DDP owns shared-gradient execution

PyTorch DDP owns ordinary model wrapping, gradient bucketing, initial synchronization,
and gradient reduction wherever its qualified behavior fits. ClanBasedTuning may
configure or narrowly specialize the framework boundary, but it does not reimplement
normal all-reduce.

The integration milestone must prove that native synchronization does not erase
intended member divergence.

**Status:** accepted unchanged.

## P7. Failure and planned completion are population-wide

Failure of one active member invalidates the active Clan. Planned completion occurs only
at a synchronized population boundary and ends the complete Clan. No supported path may
silently continue one member independently, shrink the active population, or redefine a
partial population as valid.

Here, population-wide or collective describes the validity rule, not a required
communication API. Detailed termination, timeout, diagnosis, scheduler recovery, and
operational behavior belong in the integration and support contracts.

**Status:** accepted; communication mechanism remains open.

## Supporting record

The reasoning and source evidence behind these decisions are recorded in:

- [Framework-alignment research report](../framework_alignment/research_report.md)
- [Framework-alignment evidence ledger](../framework_alignment/evidence_ledger.md)
- [Milestone 1 acceptance record](../framework_alignment/review_record.md)
- [Framework-alignment review audit](../framework_alignment/review_audit.md)
- [Milestone 3 system architecture](../design/system_architecture.md)
- [Milestone 3 behavioral contracts](../design/behavioral_test_contracts.md)
