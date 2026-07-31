# ClanBasedTuning system design

Status: active Milestone 3 design  
Date: 2026-07-31

## Purpose

This directory defines the accepted behavioral target and system lifecycle for a
PBT-shaped CBT Tune scheduler, a thin worker-side collective controller, and Lightning
DDP.

The design governs Milestone 3 implementation unless direct framework evidence or
human review explicitly reopens a clause. It does not replace the product roadmap,
project decisions, milestone gates, or framework-alignment research.

## Reader path

1. Read the [behavioral test contracts](behavioral_test_contracts.md) for the
   black-box training outcomes the completed system must prove.
2. Read the [system architecture](system_architecture.md), beginning with the exact
   imperative Tune function and state-authority tables.
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
→ apply this trial's current genome from config
→ train and evaluate
→ set local fitness on the controller
→ ask whether this worker should save
→ report metrics with a checkpoint only from the selected worker
```

The worker controller owns only the fitness collective and local boolean save decision.
Lightning owns distributed training and checkpoint construction.

The CBT Tune scheduler owns:

- associating reported fitness with each trial's active genome;
- selecting the winner;
- attaching the winning parent genome to checkpoint metadata;
- deriving and installing one child genome per target trial;
- assigning the selected checkpoint to every target; and
- mutation RNG, persistence, and replay lineage.

## Genome and checkpoint distinction

The current member genome is the controlled subset of that member's `Trial.config`.
The winner checkpoint contains the common training continuation. Its metadata records
which parent genome produced it, but each receiving member's child genome remains in
that target member's Tune configuration.

Therefore the next population is formed from:

```text
one common selected checkpoint
+
one scheduler-assigned child genome per target Trial.config
```

## Artifact roles

### Behavioral test contracts

The contracts observe CBT as part of an ordinary training system. They may supply
fitness to CBT and inspect model state, optimizer state, training progress,
checkpoints, controlled values, and later updates. They do not freeze internal
scheduler methods or framework-private objects merely to make assertions convenient.

### System architecture

The architecture provides:

- the exact intended Tune function shape;
- genome, scheduler, worker, and checkpoint authority;
- the parent-genome checkpoint metadata schema;
- the lifecycle and checkpoint ordering;
- a two-round example;
- failure and support boundaries; and
- the framework seams implementation must qualify.

## Design boundary

CBT defines no Ray `Trainable` subclass and no second training loop. Ray may internally
wrap the user function in its own `FunctionTrainable`; that remains Ray's implementation
detail.

The eventual `make_cbt_controller()` factory hides rank, collective membership, and
comparison context. The framework-independent slice currently implements the thin
controller, shared selection rule, mutation primitive, and checkpoint-provenance
metadata builder. Ray collective construction, the Tune scheduler, and Lightning
checkpoint integration remain subsequent Milestone 3 work.
