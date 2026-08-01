# Milestone 2 gates — evolutionary subsystem

Status: closed historical gate; runtime shape superseded by Milestone 3  
Original date: 2026-07-25  
Supersession recorded: 2026-07-31

## Historical result

Milestone 2 established framework-independent population-selection and mutation
behavior before a Ray invocation path had been selected.

The work proved:

- minimizing and maximizing selection with stable lower-rank tie behavior;
- bounded linear and logarithmic optimizer-hyperparameter mutation;
- deterministic mutation from explicit random state;
- complete-population requirements;
- failure before partial evolutionary output; and
- separation from model, optimizer, checkpoint, training, and Ray runtime ownership.

Those algorithms remain useful.

## Superseded runtime design

The Milestone 2 implementation later expressed those algorithms through a public
`ClanRound` and a persistent per-process `ClanController` that loaded a complete
population, selected a winner, mutated a next configuration, advanced a hidden round,
and serialized controller state.

The accepted Milestone 3 Tune lifecycle showed that this object model duplicated
framework responsibilities:

- Tune trial configuration is the natural live genome authority;
- the Tune scheduler is the natural mutation, lineage, and checkpoint-assignment
  authority;
- the worker needs only a pre-report collective checkpoint-source decision; and
- the selected training checkpoint must remain separate from target-local child
  genomes.

Therefore the public `ClanRound`, controller advancement, controller-owned mutation,
and controller checkpoint state are no longer active requirements. They are historical
evidence rather than current architecture.

## Retained Milestone 2 products

### Mutation rules

`MutationSpec` remains the framework-independent description of one bounded controlled
value mutation. The future CBT Tune scheduler owns the random stream and applies these
rules while constructing target trial genomes.

### Stable selection

The stable population comparison remains a shared internal primitive. Worker-side
checkpoint-source resolution and scheduler-side winner verification must use the same
rule.

### Validation philosophy

The project continues to prefer small corruption guards at real authority boundaries:
finite fitness, complete population, declared mutation geometry, and bounded output.
It does not construct a broad validation subsystem around trusted internal objects.

### Framework independence

Core selection, mutation, and checkpoint-provenance metadata construction remain plain
Python and do not import Ray or Lightning.

## Current authority

The active Milestone 3 gate and system architecture govern all implementation work:

- [Milestone 3 gate](milestone_3_integratable_orchestration.md)
- [System architecture](../../design/system_architecture.md)
- [Worker controller reference](../../controller/README.md)

No implementation should restore the superseded Milestone 2 lifecycle merely to satisfy
this historical gate.
