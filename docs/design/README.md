# ClanBasedTuning system design

Status: active Milestone 3 design  
Date: 2026-07-31

## Purpose

This directory defines the accepted behavioral target and system lifecycle for a
PBT-shaped CBT Tune scheduler, a thin worker-side controller, and Lightning DDP.

The design governs Milestone 3 implementation unless direct framework evidence or
human review explicitly reopens a clause. It does not replace the product roadmap,
project decisions, milestone gates, or framework-alignment research.

## Reader path

1. Read the [behavioral test contracts](behavioral_test_contracts.md) for the
   black-box training outcomes the completed system must prove.
2. Read the [system architecture](system_architecture.md), beginning with the exact
   imperative Tune function and state-authority table.
3. Consult the governing [product roadmap](../product_roadmap.md), accepted
   [project decisions](../decisions/project_decisions.md), and
   [Milestone 3 gate](../milestones/gates/milestone_3_integratable_orchestration.md)
   when judging scope or milestone completion.
4. Consult the accepted
   [framework-alignment research](../framework_alignment/README.md) for the
   evidence and ownership model behind the design.

## Governing user flow

CBT should feel like ordinary Tune PBT plus one worker-side save decision and one
winner-side provenance write:

```text
read the scheduler-assigned genome from config
→ construct the worker controller with a copy of that genome
→ obtain any Tune-assigned checkpoint
→ restore training state
→ apply the current genome
→ train and evaluate
→ set local fitness on the controller
→ ask whether this worker should save
→ selected worker constructs the checkpoint
→ selected worker saves its genome into checkpoint metadata
→ report metrics with a checkpoint only from that worker
```

The worker controller owns only:

- the immutable current-round genome snapshot used for provenance;
- the fitness collective;
- the local boolean save decision; and
- winner-only `save_genome(checkpoint)`.

It does not mutate genomes or own future assignments.

Lightning owns distributed training and checkpoint construction.

The CBT Tune scheduler owns:

- associating reported fitness with each trial's active genome;
- independently selecting and verifying the winner;
- verifying the checkpoint's producer metadata;
- deriving and installing one child genome per target trial;
- assigning the selected checkpoint to every target; and
- mutation RNG, persistence, recovery, and replay lineage.

## Genome, scheduler, and checkpoint distinction

The scheduler is the evolutionary authority.

Each member's `Trial.config` is the scheduler's materialized genome assignment for the
current round. The controller copies that assignment so the selected worker can record
what produced its checkpoint.

The winner checkpoint contains:

```text
Lightning training continuation
+
producer metadata: schema version, member ID, and genome
```

The metadata is evidence, not a second source of child-genome authority. Receiving
child genomes remain scheduler assignments carried through the target trial
configurations.

Therefore the next population is formed from:

```text
one common selected and producer-annotated checkpoint
+
one scheduler-assigned child genome per target Trial.config
```

## Ordering and atomicity

The winner annotates the checkpoint before `tune.report()`:

```text
construct checkpoint payload
→ controller.save_genome(checkpoint)
→ report complete artifact
```

A failed metadata write prevents publication of an incomplete artifact.

The later scheduler transition has a separate commit boundary. No next-round trial may
run until winner verification, child derivation, scheduler persistence, target config
installation, and common checkpoint assignment are all complete.

## Artifact roles

### Behavioral test contracts

The contracts observe CBT as part of an ordinary training system. They may supply
fitness to CBT and inspect model state, optimizer state, training progress, trial
configurations, checkpoint artifacts, controlled values, scheduler recovery, and later
training behavior. They do not freeze framework-private objects merely to make
assertions convenient.

### System architecture

The architecture provides:

- the exact intended Tune function shape;
- scheduler, worker, trial-config, and checkpoint responsibilities;
- the minimal producer-genome metadata schema;
- the lifecycle and checkpoint ordering;
- transition atomicity and failure boundaries;
- a two-round example; and
- the framework seams implementation must qualify.

## Module boundary

Package organization must reflect ownership:

- worker controller behavior belongs in `controller.py`;
- shared winner comparison belongs in a selection module;
- mutation rules belong in an evolution or scheduler-types module;
- Tune lifecycle and scheduler state belong in the scheduler integration; and
- Ray collective construction belongs in the worker runtime integration.

Mutation and scheduler metadata concerns do not belong in `controller_types.py` merely
because an older controller design once owned evolution.

## Design boundary

CBT defines no Ray `Trainable` subclass and no second training loop. Ray may internally
wrap the user function in its own `FunctionTrainable`; that remains Ray's implementation
detail.

The eventual `make_cbt_controller(genome=...)` factory hides rank, collective
membership, and comparison context. The framework-independent implementation currently
has the thin save-decision controller but still requires the genome snapshot,
`save_genome(checkpoint)`, module split, Ray collective construction, Tune scheduler,
and Lightning checkpoint integration described by the active architecture.
