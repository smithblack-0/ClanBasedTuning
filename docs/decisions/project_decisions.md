# ClanBasedTuning project decisions

Status: proposed project decisions for Milestone 1 acceptance  
Date: 2026-07-24

## Purpose

This file records dated technical decisions that resolve choices left open by
the governing [product roadmap](../product_roadmap.md). They remain proposed
until Milestone 1 human review accepts them. Once accepted, later work may rely
on them unless a newer explicit decision supersedes them.

This file contains only durable cross-milestone choices. Milestone completion
requirements, research evidence, active implementation plans, temporary support
limits, and framework-version qualification belong in their own artifacts.

## P1. One Ray Tune trial represents one live Clan member

In the Ray-backed program, one Tune trial represents one Clan member. Every
member that contributes to shared-gradient training must be concurrently live;
time-multiplexing or silently omitting a member changes the method.

Ray's generated trial set remains the population authority. Integration and
usability work must make trial count, concurrent capacity, Clan membership,
rank/world-size assignment, and dedicated resources describe one coherent live
population.

## P2. Lightning produces the qualifying round boundary

A Clan round ends at a qualifying Lightning validation-and-checkpoint event.
Lightning owns the training and validation cadence that produces the event; a
Clan controller consumes the completed population result rather than maintaining
a second progress clock.

The integration milestone must define which Lightning events qualify and prove
that every live member reaches the same logical boundary.

## P3. ClanBasedTuning decides the population transition; native frameworks execute it

The evolutionary controller owns the Clan-specific population decision: compare
one complete population, select the sole parent whose model and optimizer state
become the basis of the next generation, and produce the next member optimizer
configurations.

In the Ray/Lightning path, native framework machinery executes that decision:
Ray Tune owns trial lifecycle and checkpoint/configuration assignment, while
Lightning owns checkpoint contents and restoration. After Lightning restores
the inherited optimizer state, ClanBasedTuning reapplies only the receiving
member's evolved optimizer values.

This decision does not choose whether Milestone 2 implements the controller by
specializing an existing PBT scheduler or by building a direct controller with a
thin framework adapter. Milestone 2 must choose the narrowest design that
expresses the policy without duplicating ordinary Tune lifecycle behavior.

No separate Clan checkpoint scheduler, generation manifest, or optimizer
construction system is introduced without direct evidence of a native gap.

## P4. Training data is partitioned; fitness data is comparable

Training retains normal distributed partitioning. Every member is evaluated on
the same held-out workload under comparable conditions, and each fitness value
remains member-local until the population controller compares the candidates.

The integration milestone defines and proves the concrete sampler, metric,
boundary, and reporting contract.

## P5. Native PyTorch distributed strategies own shared-gradient execution

PyTorch's qualified distributed strategy owns ordinary model wrapping, initial
state synchronization, gradient bucketing, and gradient collectives.
ClanBasedTuning may configure or narrowly specialize a framework boundary where
intentional member divergence requires it, but it does not reimplement ordinary
gradient reduction.

The first complete integration qualifies DDP. Later support for FSDP or another
model-sharding strategy must preserve the same Clan semantics through that
strategy's native lifecycle rather than creating a separate distributed
implementation.

## P6. Active-population validity and planned completion are collective

An active Clan is the complete population participating in one shared-gradient
workflow. If a required member is missing or fails, the current Clan is invalid;
the system may not silently continue with a smaller population or redefine the
survivors as the same Clan.

Planned completion occurs only at a coherent population boundary and applies to
the complete Clan. The exact framework behavior for termination, diagnosis, and
operational recovery becomes enforceable where the roadmap introduces the
corresponding integration or industry capability; it is not a separate
controller-owned recovery subsystem.

## Supporting record

The reasoning and source evidence behind these proposed decisions are recorded
in:

- [Framework-alignment research report](../framework_alignment/research_report.md)
- [Framework-alignment evidence ledger](../framework_alignment/evidence_ledger.md)
