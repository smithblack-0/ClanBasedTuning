# ClanBasedTuning system design

Status: active Milestone 3 design  
Date: 2026-07-31  
Population-resolution clarification: 2026-08-01

## Purpose

This directory defines the accepted behavioral target and system lifecycle for a
PBT-shaped CBT Tune scheduler, a thin worker-side controller, and Lightning DDP.

The design governs Milestone 3 implementation unless direct framework evidence or
human review explicitly reopens a clause. The population-resolution mechanism is
currently reopened and must not be inferred from older controller code or rejected
branches.

## Reader path

1. Read the [behavioral test contracts](behavioral_test_contracts.md) for the black-box
   outcomes the completed system must prove.
2. Read the [system architecture](system_architecture.md) for lifecycle, ownership, and
   open integration seams.
3. Consult the governing [product roadmap](../product_roadmap.md), accepted
   [project decisions](../decisions/project_decisions.md), and
   [Milestone 3 gate](../milestones/gates/milestone_3_integratable_orchestration.md).
4. Consult the accepted
   [framework-alignment research](../framework_alignment/README.md) before choosing a
   version-sensitive framework seam.

## Governing user flow

CBT should retain the ordinary Tune function shape:

```text
read the scheduler-assigned genome from config
→ construct the worker controller with a copied genome snapshot
→ obtain any Tune-assigned checkpoint
→ restore training state
→ apply the current genome
→ train and evaluate
→ provide local fitness to the controller
→ obtain the local checkpoint-source decision
→ selected worker constructs and annotates the checkpoint
→ report metrics, with a checkpoint only from that worker
```

The high-level ordering is accepted. The mechanism that turns the complete population's
fitness into one pre-report checkpoint-source decision is not yet accepted.

## Responsibility split

The worker controller owns only:

- one copied current-round genome snapshot for producer provenance;
- one local fitness value;
- one cached local checkpoint-source decision supplied through the runtime integration;
  and
- winner-only producer metadata attachment.

It does not own mutation, future assignments, scheduler recovery, or communication
backend selection.

Lightning owns distributed training and checkpoint construction.

The CBT Tune scheduler owns:

- associating reported fitness with each trial's active genome;
- selecting and verifying the winner;
- verifying checkpoint producer metadata;
- deriving and installing one child genome per target trial;
- assigning the selected checkpoint to every target; and
- mutation RNG, persistence, recovery, and replay lineage.

## Genome, scheduler, and checkpoint distinction

The scheduler is the evolutionary authority. Each member's `Trial.config` materializes
its scheduler-assigned genome for the current round.

The controller owns an independent copied mapping used only to record what produced the
selected checkpoint. The design does not currently require deep immutability for
arbitrary nested values.

The winner checkpoint contains:

```text
Lightning training continuation
+
producer metadata: schema version, member ID, and genome
```

The metadata is evidence, not child-genome authority. The next population combines one
common selected checkpoint with one scheduler-assigned child genome per target trial.

## Ordering and atomicity

The selected worker completes producer annotation before reporting:

```text
construct checkpoint payload
→ attach producer metadata
→ report complete artifact
```

A failed annotation prevents publication of an incomplete winner artifact.

The scheduler transition has a separate commit boundary. No next-round trial may run
until winner verification, child derivation, scheduler persistence, target-config
installation, and common-checkpoint assignment are complete.

## Open population-resolution seam

The complete active population must reach one consistent decision about which member
may report the checkpoint. The accepted requirements are:

- every required member participates at the same logical boundary;
- one comparable fitness is associated with each stable member;
- all participants use the same accepted comparison and tie rule;
- exactly one member receives the checkpoint-source result;
- a missing or failed member invalidates the boundary; and
- repeated local queries return the cached decision without repeating synchronization.

The design does **not** yet choose:

- Ray collectives;
- the existing PyTorch distributed process group;
- an all-gather operation;
- an injected callback signature;
- rank-to-member mapping mechanics;
- timeout and failure release behavior; or
- the module that will implement the runtime seam.

Those choices require a fresh current-iteration design and direct framework evidence.

## Module boundary

Current accepted package organization is:

- `controller.py` for the worker-local controller;
- `evolution.py` for `MutationSpec`, stable winner selection, and future pure evolution
  logic;
- `scheduler_types.py` for dictionary aliases only; and
- a future scheduler module for Tune lifecycle, mutation state, lineage, persistence,
  target configurations, and checkpoint assignment.

The population-resolution integration module is intentionally unnamed until its
framework ownership is settled. There is no accepted `selection.py` or
`ray_collective.py` requirement.

## Current implementation status

The active package contains the evolution primitives and a provisional thin controller.
The controller's current `exchange_fitness` callback, associated naming, docstrings, and
fake unit-test transport are inherited from PR #33 and are not the accepted production
seam. They require cleanup before genome provenance or framework integration proceeds.

No production communication backend, controller genome snapshot, `save_genome()`, Tune
scheduler, or Lightning checkpoint integration is currently accepted as implemented.
