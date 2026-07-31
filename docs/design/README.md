# ClanBasedTuning system design

Status: proposed design package under human review  
Date: 2026-07-31

## Purpose

This directory translates the governing roadmap, accepted project decisions,
framework evidence, and behavioral test contracts into one coherent proposed
system design.

The design is not implementation and does not establish milestone completion.
Until human review accepts it, it is a proposal. After acceptance, it governs the
component responsibilities and lifecycle described here unless later evidence
reopens a specific clause.

## Reader path

1. Read the [behavioral test contracts](behavioral_test_contracts.md) for the
   outcomes any acceptable implementation must prove.
2. Read the [system architecture](system_architecture.md) for the proposed owners,
   state partitions, framework seams, and complete round lifecycle.
3. Consult the governing [product roadmap](../product_roadmap.md), accepted
   [project decisions](../decisions/project_decisions.md), and
   [Milestone 3 gate](../milestones/gates/milestone_3_integratable_orchestration.md)
   when judging scope or authority.
4. Consult the accepted
   [framework-alignment research](../framework_alignment/README.md) for the
   evidence and responsibility model behind the design.

## Artifact roles

### Behavioral test contracts

The contracts state observations whose failure would prove that the implemented
Clan behavior is wrong. They partition state explicitly and avoid prescribing a
class, callback, scheduler, public facade, or framework extension point merely to
make a test convenient.

### System architecture

The architecture assigns every material responsibility and state transition to
one owner. It identifies the narrow custom seams required to compose Ray Tune,
Lightning, and PyTorch DDP without introducing a second training loop,
checkpoint system, population policy, or gradient implementation.

## Review boundary

This design PR should answer one review question:

> Does this responsibility and lifecycle model provide a coherent foundation for
> implementing Clan Tuning through the accepted frameworks?

Implementation sequencing, milestone-sized PR decomposition, and executable test
construction follow after the design is accepted. They should not be inferred
from document section order.
