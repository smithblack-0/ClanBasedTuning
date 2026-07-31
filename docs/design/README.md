# ClanBasedTuning system design

Status: active Milestone 3 design  
Date: 2026-07-31

## Purpose

This directory defines the accepted behavioral target and system lifecycle for
composing a PBT-shaped CBT Tune scheduler, a thin worker-side collective controller,
and Lightning DDP.

The design governs Milestone 3 implementation unless direct framework evidence or
human review explicitly reopens a clause. It does not replace the product roadmap,
project decisions, milestone gates, or framework-alignment research.

## Reader path

1. Read the [behavioral test contracts](behavioral_test_contracts.md) for the
   black-box training outcomes the completed system must prove.
2. Read the [system architecture](system_architecture.md), beginning with the exact
   imperative Tune function that CBT intends to support.
3. Consult the governing [product roadmap](../product_roadmap.md), accepted
   [project decisions](../decisions/project_decisions.md), and
   [Milestone 3 gate](../milestones/gates/milestone_3_integratable_orchestration.md)
   when judging scope or milestone completion.
4. Consult the accepted
   [framework-alignment research](../framework_alignment/README.md) for the
   evidence and ownership model behind the design.

## Governing user flow

CBT should feel like ordinary Tune PBT plus one worker-side save decision:

```text
construct the worker controller
→ obtain any Tune-assigned checkpoint
→ restore training state
→ apply this trial's current optimizer configuration
→ train and evaluate
→ set local fitness on the controller
→ ask whether this worker should save
→ report metrics with a checkpoint only from the selected worker
```

The CBT Tune scheduler owns evolutionary policy and checkpoint redistribution. The
worker controller owns only the fitness collective and local boolean save decision.
Lightning owns distributed training and checkpoint construction.

## Artifact roles

### Behavioral test contracts

The contracts observe CBT as part of an ordinary training system. They may supply
fitness to CBT and inspect model state, optimizer state, training progress,
checkpoints, and later updates. They do not freeze internal winner identifiers,
comparison option names, callback order, or scheduler methods.

### System architecture

The architecture provides:

- the exact intended Tune function shape;
- the lifecycle and checkpoint ordering;
- the responsibility split between the worker controller, Tune scheduler, Lightning
  DDP, and user train function;
- a two-round example and sequence diagram;
- failure and support boundaries; and
- the framework seams implementation must qualify.

## Design boundary

CBT defines no Ray `Trainable` subclass and no second training loop. Ray may internally
wrap the user function in its own `FunctionTrainable`; that remains Ray's implementation
detail.

The eventual `make_cbt_controller()` factory hides rank, collective membership, and
comparison context. The framework-independent slice currently implements only the thin
controller contract; Ray collective construction and the scheduler remain subsequent
Milestone 3 work.
