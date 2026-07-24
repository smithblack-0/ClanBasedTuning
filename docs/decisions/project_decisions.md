# ClanBasedTuning project decisions

Status: proposed project decisions for Milestone 1 acceptance  
Date: 2026-07-24

## Purpose

This file records dated technical decisions that resolve choices left open by
the governing [product roadmap](../product_roadmap.md). Once accepted, later
milestones may rely on them unless a newer explicit decision supersedes them.

This file does not contain milestone completion gates, audit history, temporary
support limits, or implementation plans. Those belong to the milestone and
research artifacts that own them.

## P1. One Ray Tune trial represents one live Clan member

One Tune trial represents one Clan member. The complete population must be
concurrently resident, and every member participates in every shared training
gradient.

Ray remains the population authority. Later assembly work must make the
generated trial count, concurrent capacity, Clan world size, and dedicated
resources describe one consistent live population.

## P2. Lightning produces the evolutionary boundary

A Clan round ends at a qualifying Lightning validation-and-checkpoint event.
Lightning owns the training and validation cadence that produces the event; the
evolutionary controller consumes it rather than maintaining a second progress
clock.

The integration milestone must define which Lightning events qualify and prove
that all members reach them coherently.

## P3. The evolutionary subsystem specializes synchronous Ray PBT

The evolutionary subsystem will be implemented as a narrow specialization of
synchronous Ray `PopulationBasedTraining`.

Ray PBT already owns population synchronization, source-checkpoint preparation,
checkpoint and configuration transfer, pause, resume, and scheduler persistence.
ClanBasedTuning changes the population decision: one deterministic parent, one
elite configuration, all other members targeted, and optimizer-only mutation.

This decision is reopened only if Milestone 2 contract tests show that the
available seam cannot express the transition without reproducing substantial
Tune controller behavior.

## P4. Ray transfers state; Lightning defines and restores it

Lightning owns checkpoint contents and restoration. Ray PBT owns source
selection and checkpoint assignment to target trials. After Lightning restores
the parent's optimizer state, ClanBasedTuning reapplies only the receiving
member's evolved optimizer configuration.

This division does not create a separate Clan checkpoint scheduler, generation
manifest, or optimizer-construction system.

## P5. Training data is partitioned; fitness data is comparable

Training retains normal distributed partitioning. Every member is evaluated on
the same held-out workload under comparable conditions, and each fitness value
remains local to its Tune trial until Ray compares the population.

The integration milestone owns the concrete sampler, metric, and reporting
contract.

## P6. Native PyTorch DDP owns shared-gradient execution

PyTorch DDP owns ordinary model wrapping, gradient bucketing, initial
synchronization, and gradient collectives wherever its qualified behavior fits.
ClanBasedTuning may configure or narrowly specialize the framework boundary, but
it does not reimplement normal all-reduce.

The integration milestone must prove that native synchronization does not erase
intended member divergence.

## P7. Failure and planned completion are collective

Failure of one active member invalidates the active Clan. Planned completion
occurs only at a synchronized population boundary and ends the complete Clan.

Milestones 2, 3, and 6 qualify native framework recovery at controller,
integration, and production scope. None may silently continue one member
independently, shrink the active population, or redefine a partial population
as a valid Clan.

## Supporting record

The reasoning and source evidence behind these decisions are recorded in:

- [Framework-alignment research report](../framework_alignment/research_report.md)
- [Framework-alignment evidence ledger](../framework_alignment/evidence_ledger.md)
