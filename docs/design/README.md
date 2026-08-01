# ClanBasedTuning system design

Status: active Milestone 3 design  
Date: 2026-07-31

## Purpose

This directory defines the accepted behavioral target and system lifecycle for a
PBT-shaped CBT Tune scheduler, a thin worker controller, a Ray collective
population-resolution boundary, and Lightning DDP.

The design distinguishes fixed architecture from implementation choices. A merged
prototype or callback does not become an accepted contract unless the governing design
and evidence gates say so.

## Reader path

1. Read the [system architecture](system_architecture.md) for the complete lifecycle and
   state ownership.
2. Read the [Ray population-resolution design](population_resolution.md) for the fixed
   Ray invariants and still-open interface choices.
3. Read the [behavioral test contracts](behavioral_test_contracts.md) for observable
   acceptance behavior.
4. Consult the governing [product roadmap](../product_roadmap.md),
   [project decisions](../decisions/project_decisions.md), and
   [Milestone 3 gate](../milestones/gates/milestone_3_integratable_orchestration.md).
5. Consult the accepted
   [framework-alignment research](../framework_alignment/README.md) before choosing a
   version-sensitive framework seam.

## Governing user flow

CBT preserves the ordinary Tune function shape:

```text
read the scheduler-assigned genome from config
→ construct the worker controller with a copied genome mapping
→ obtain any Tune-assigned checkpoint
→ restore training state
→ apply the current genome
→ train and evaluate through Lightning
→ provide one local fitness
→ resolve one checkpoint source through the Ray population collective
→ selected member constructs and annotates the checkpoint
→ report metrics, with a checkpoint only from that member
```

The high-level ordering and Ray-collective requirement are accepted.

The exact Ray primitive, exchanged result shape, stable member/rank representation,
controller/runtime collaborator boundary, and final names remain under design review.

## Responsibility summary

The worker controller owns:

- one copied current-genome mapping for provenance;
- one local fitness;
- participation in one Ray population-resolution boundary through the runtime
  integration;
- one cached local checkpoint-source decision; and
- winner-only producer metadata writing.

The Ray runtime owns collective membership, transport, generation isolation, timeout,
and failure behavior.

The framework-independent evolution policy owns mutation and deterministic winner
selection.

Lightning owns distributed training and checkpoint construction.

The CBT Tune scheduler owns result association, winner verification, child-genome
derivation, mutation and lineage state, target configuration, recovery, and checkpoint
redistribution.

## Genome and checkpoint distinction

The scheduler is the evolutionary authority. Each member's `Trial.config` materializes
its assigned current genome.

The controller receives an independently copied mapping so the selected worker can
record what produced its checkpoint. The contract is copied mapping ownership, not deep
immutability of arbitrary nested values.

The selected checkpoint contains:

```text
Lightning training continuation
+
producer metadata: schema version, stable member ID, copied genome
```

Producer metadata is evidence, not child-genome authority.

## Atomicity

The winner artifact is completed before reporting:

```text
construct checkpoint payload
→ attach producer metadata
→ report complete artifact
```

The scheduler transition has a separate commit boundary:

```text
verify complete generation
→ derive all child genomes
→ persist scheduler transition state
→ assign all configs and checkpoints
→ release complete next population
```

## Current implementation boundary

The active package currently contains:

- a framework-independent `ClanController` with a provisional
  `exchange_fitness(local_fitness) -> Sequence[float]` callback;
- `MutationSpec` and `select_winner_id()` in `evolution.py`; and
- dictionary aliases in `scheduler_types.py`.

The callback name, sequence-position identity, callable shape, and responsibility split
are not accepted design merely because they are merged.

The active package does not yet contain an accepted Ray population-resolution runtime,
controller genome provenance, `make_cbt_controller()`, the CBT Tune scheduler, Lightning
integration, or a repeated end-to-end generation path.

## Module boundary

Accepted current modules are:

- `controller.py` for worker-local boundary state;
- `evolution.py` for pure selection, mutation, and later child-genome logic;
- `scheduler_types.py` for dictionary aliases only; and
- future `scheduler.py` for Tune generation transitions.

The Ray runtime module and collaborator names remain deliberately unfixed until the
population-resolution interface is reviewed. The design does not require a separate
`selection.py` or a module literally named `ray_collective.py`.
