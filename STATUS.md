# ClanBasedTuning project status

Last updated: 2026-07-31

## Current position

Milestone 1 established the framework-alignment research, project decisions, roadmap,
milestone gates, and durable engineering process.

Milestone 2 established framework-independent selection and mutation primitives. Its
later persistent `ClanRound` and evolutionary-controller lifecycle has been superseded.

Milestone 3 now has the high-level lifecycle in place but is paused for a design cleanup
before more runtime work.

The accepted lifecycle is:

- one live Tune trial per stable Clan member;
- one complete concurrently resident population;
- one Lightning DDP world for shared-gradient training;
- one Ray collective population-resolution boundary per generation;
- one deterministic checkpoint source known before Tune reporting;
- one selected Lightning checkpoint annotated by its producer before reporting;
- one CBT Tune scheduler authoritative over genomes, mutation, lineage, recovery,
  target configurations, and checkpoint redistribution; and
- one all-or-nothing scheduler transition into the next population.

## Ray population-resolution state

The Ray-collective architecture is accepted.

The complete active population must:

1. contribute one comparable local fitness per stable member at the same logical
   Lightning boundary;
2. associate every fitness with the correct stable member;
3. prevent cross-generation operation mixing;
4. apply the same deterministic selection and tie policy used by the scheduler;
5. reach the same selected stable member on every participant;
6. let exactly one member retain and report the checkpoint;
7. cache each local save decision so later checks perform no second collective; and
8. fail the complete boundary on missing, failed, duplicated, malformed, or mixed-
   generation participation.

The following implementation choices remain under review:

- exact Ray collective primitive or composition;
- whether the worker-side result is member-associated fitness or the selected member ID;
- whether stable member identity is proven equal to Ray rank or communicated explicitly;
- the controller-versus-Ray-runtime collaborator boundary;
- final class, method, and module names;
- timeout and surfaced failure behavior; and
- exact generation-isolation and multiprocess test mechanisms.

## Current implementation

The active source contains:

- `ClanController`, which stores one finite local fitness, calls a provisional
  `exchange_fitness(local_fitness)` callback, selects one winner, and caches the local
  save decision;
- `MutationSpec` and `select_winner_id()` in `evolution.py`; and
- dictionary aliases in `scheduler_types.py`.

The current controller assumes the returned fitness sequence is ordered by stable member
identity. That callback name, callable shape, ordering assumption, validation placement,
and responsibility split are transitional code rather than accepted design.

The active source does **not** contain:

- an accepted Ray population-resolution runtime;
- controller genome snapshot or `save_genome(checkpoint)`;
- `make_cbt_controller()`;
- the CBT Tune scheduler;
- Lightning DDP integration or winner-aware checkpoint persistence;
- optimizer-config application after restore; or
- a repeated end-to-end generation path.

## Genome and checkpoint model

The CBT Tune scheduler decides current and next population genomes. The controlled subset
of one active member's `Trial.config` is that member's scheduler assignment.

The worker controller will later receive an independently copied mapping of that genome
for producer provenance. The contract is separate mapping ownership, not recursive
immutability of arbitrary nested values.

The selected worker will write:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

before reporting the checkpoint. It will not write generation index, Tune trial ID,
fitness, child genomes, mutation state, or lineage.

The scheduler will independently verify the selected member and metadata, derive all
child genomes, persist mutation/lineage/recovery state, assign the common checkpoint and
target configs, and release the next population only after the transition is complete.

## Current work order

The next work is design-first rather than implementation-first:

1. review and accept the intrinsic Ray population-resolution requirements;
2. choose the Ray primitive, result shape, identity contract, component boundary, names,
   timeout behavior, and generation-isolation mechanism;
3. rewrite the controller and direct documentation from that accepted interface rather
   than renaming the provisional callback;
4. add the controller genome snapshot and winner-only producer metadata boundary;
5. qualify the chosen Ray runtime against the pinned version;
6. implement the CBT Tune scheduler;
7. implement Lightning DDP and winner-aware checkpoint integration; and
8. prove at least two complete real generations.

Each PR must state its exact diff, inherited assumptions, evidence level, and exclusions.
A fake callback test must not be described as Ray collective evidence.

## Atomicity requirements

The selected checkpoint must be fully annotated before it is reported. A failed metadata
write prevents publication.

The scheduler has a separate transition commit boundary. No next-round worker may run
until winner verification, child derivation, scheduler-state persistence, target-config
installation, and common-checkpoint assignment are complete.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone 3 gate](docs/milestones/gates/milestone_3_integratable_orchestration.md)
- [System architecture](docs/design/system_architecture.md)
- [Ray population-resolution design](docs/design/population_resolution.md)
- [Behavioral test contracts](docs/design/behavioral_test_contracts.md)
- [Worker controller reference](docs/controller/README.md)
- [Framework-alignment package](docs/framework_alignment/README.md)

## Known limitations

- The active controller communication interface is provisional.
- There is no active Ray-backed controller factory.
- There is no active CBT Tune scheduler.
- There is no active Lightning DDP integration or winner-aware checkpoint path.
- There is no live optimizer-configuration application system.
- Version-sensitive Tune checkpoint assignment and scheduler recovery require direct
  framework-contract qualification.
- Historical and rejected branches remain evidence only and must not be reused as
  current-iteration implementation authority.
