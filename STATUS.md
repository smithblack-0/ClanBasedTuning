# ClanBasedTuning project status

Last updated: 2026-07-31

## Current position

Milestone 1 established the accepted framework-alignment research, project decisions,
roadmap, milestone gates, and durable engineering process.

Milestone 2 established the initial framework-independent selection and mutation
algorithms. Its later per-process `ClanRound` and persistent evolutionary-controller
shape has been superseded by the Milestone 3 lifecycle.

Milestone 3 retains a thin worker controller and a scheduler-authoritative evolutionary
model, with one corrected provenance boundary:

- `ClanController` remains an ephemeral worker-side fitness collective and
  checkpoint-source decision;
- the intended controller additionally copies the current assigned genome and lets only
  the selected worker call `save_genome(checkpoint)`;
- the winning checkpoint is annotated before reporting with only schema version,
  stable member ID, and the exact genome that produced it;
- the CBT Tune scheduler remains authoritative over population genomes, mutation,
  lineage, recovery, target configurations, and checkpoint assignment; and
- Lightning remains authoritative over model, optimizer, training progress, and
  checkpoint construction.

There is no active public `ClanRound`, controller advancement protocol, controller
mutation authority, or checkpointed evolutionary controller.

## Governing state model

The CBT Tune scheduler decides the current and next population genomes.

For one active member, the controlled subset of its `Trial.config` is the scheduler's
materialized genome assignment. The worker copies that same mapping into its controller
and applies it to the optimizer.

The controller copy is not another genome authority. It exists only so the selected
worker can bind its completed checkpoint to the values that produced it before
`tune.report()` publishes the artifact.

The winner metadata schema is:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

The controller does not write a round index or Tune trial ID because it does not own
those scheduler facts. It does not write fitness, child genomes, mutation random state,
or lineage.

At a completed generation, the CBT Tune scheduler will:

1. associate each reported fitness with the reporting trial's active genome;
2. identify and verify the sole winner and checkpoint source;
3. verify the checkpoint member ID and genome against that winner;
4. derive one child genome per target trial;
5. persist mutation RNG, replay lineage, and recovery state;
6. install those child genomes in the targets' Tune configurations;
7. assign the same winning training checkpoint to every target; and
8. release the complete next population only after the transition is durably complete.

The checkpoint producer metadata is evidence. It does not own child genomes or future
scheduler decisions.

## Current implementation

The active source currently contains:

- the thin `ClanController` fitness and save-decision behavior;
- `MutationSpec`;
- one shared stable winner-selection rule; and
- the older parent-genome metadata builder.

The source does **not yet** contain the corrected genome snapshot or
`save_genome(checkpoint)` API.

The current module layout is transitional and inconsistent with the accepted ownership
model:

- `MutationSpec` belongs in an evolution or scheduler-types module;
- shared winner comparison belongs in a neutral selection module; and
- scheduler metadata concerns do not belong in `controller_types.py`.

## Current work

The next Milestone 3 implementation slices are:

1. correct the framework-independent controller and module boundaries:
   - add copied `genome` construction state;
   - add winner-only `save_genome(checkpoint)`;
   - replace the old metadata schema with `{schema_version, member_id, genome}`;
   - move mutation and shared selection concerns to honest namespaces;
2. qualify winner-side metadata attachment against Ray 2.56, including payload
   preservation and losing/unresolved rejection;
3. implement and qualify a Ray-backed `make_cbt_controller(genome=...)` factory and
   fitness collective;
4. implement the CBT Tune scheduler's complete-generation barrier, genome association,
   winner-metadata verification, mutation, lineage, recovery, target config assignment,
   and checkpoint redistribution;
5. implement Lightning DDP setup and winner-aware checkpoint persistence; and
6. prove at least two complete rounds through a real Tune and Lightning DDP path.

Each slice must be developed tests-first and preserve the ordinary Tune function shape:

```text
read assigned genome
→ make controller with a copy
→ get assigned checkpoint
→ restore training continuation
→ apply current trial genome
→ train and evaluate
→ controller resolves whether this rank saves
→ selected rank builds checkpoint and saves genome metadata
→ report one complete optional checkpoint
→ scheduler verifies, mutates, persists, and redistributes
```

## Atomicity requirements

The selected checkpoint must be fully annotated before it is reported. A failed metadata
write prevents publication.

The scheduler has a separate transition commit boundary. No next-round worker may run
until winner verification, child derivation, scheduler-state persistence, target config
installation, and common checkpoint assignment are complete.

The exact Ray scheduler persistence and recovery seam remains a direct framework-
contract requirement.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 3 gate](docs/milestones/gates/milestone_3_integratable_orchestration.md)
- [Worker controller reference](docs/controller/README.md)
- [Milestone 3 system design](docs/design/README.md)
- [Behavioral test contracts](docs/design/behavioral_test_contracts.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

- The active controller does not yet accept or save a genome snapshot.
- There is no active Ray-backed `make_cbt_controller()` factory.
- There is no active CBT Tune scheduler.
- There is no active Lightning DDP integration or winner-aware checkpoint path.
- There is no live optimizer-configuration application system.
- The version-sensitive Tune checkpoint-assignment and scheduler-recovery seams still
  require direct framework-contract qualification.
- Historical proof-of-concept code remains evidence only and must not be restored
  wholesale as architectural authority.
