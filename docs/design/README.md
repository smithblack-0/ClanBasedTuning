# ClanBasedTuning system design

Status: active Milestone 3 design  
Date: 2026-07-31

## Purpose

This directory defines the accepted behavioral target and system lifecycle for
composing the framework-independent CBT policy with Ray Tune and Lightning DDP.
It governs Milestone 3 implementation unless direct framework evidence or human
review explicitly reopens a clause.

The design does not replace the product roadmap, project decisions, milestone
gates, or framework-alignment research. It translates them into the concrete
round lifecycle and responsibility boundaries that implementation must follow.

## Reader path

1. Read the [behavioral test contracts](behavioral_test_contracts.md) for the
   black-box training outcomes the completed system must prove.
2. Read the [system architecture](system_architecture.md) from the lifecycle
   diagram forward. It explains the complete flow before assigning component
   responsibilities.
3. Consult the governing [product roadmap](../product_roadmap.md), accepted
   [project decisions](../decisions/project_decisions.md), and
   [Milestone 3 gate](../milestones/gates/milestone_3_integratable_orchestration.md)
   when judging scope or milestone completion.
4. Consult the accepted
   [framework-alignment research](../framework_alignment/README.md) for the
   evidence and ownership model behind the design.

## Artifact roles

### Behavioral test contracts

The contracts observe CBT as part of an ordinary training system. They may supply
fitness to CBT and inspect model state, optimizer state, training progress,
checkpoints, and later updates. They do not freeze internal winner identifiers,
comparison option names, callback order, or scheduler methods.

### System architecture

The architecture begins with the governing lifecycle:

```text
load preferred continuation
→ rebase and mutate locally
→ train through Lightning DDP
→ compare the complete population through a Ray collective
→ persist one preferred Lightning checkpoint
→ report and transfer it through Tune
→ load it everywhere
```

It then explains why the order is necessary, maps it onto inspected framework
source, identifies the minimal components, and states the evidence required from
implementation.

## Design boundary

The design fixes system behavior, lifecycle order, state authority, and framework
ownership. It intentionally leaves ordinary implementation details—method
signatures, file layout, and milestone-sized issue order—to the implementation
plan, provided they do not change those contracts.

CBT supplies an ordinary Tune function for each round and defines no Ray
`Trainable` subclass. Ray may internally wrap that function in its own
`FunctionTrainable`; that remains Ray's implementation detail. Lightning owns the
training loop within each round, and Tune owns trial replacement between rounds.
