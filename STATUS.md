# ClanBasedTuning project status

Last updated: 2026-07-31

## Current position

Milestone 1 established the accepted framework-alignment research, project decisions,
roadmap, milestone gates, and durable engineering process.

Milestone 2 established the initial framework-independent selection and mutation
algorithms. Its later per-process `ClanRound` and persistent evolutionary-controller
shape has now been superseded by the accepted PBT-shaped Milestone 3 lifecycle.

Milestone 3 has an accepted system design and behavioral acceptance contract. The
current implementation contains its first corrected core slice:

- `ClanController` is an ephemeral worker-side fitness collective and checkpoint-source
  decision;
- `MutationSpec` remains the scheduler's framework-independent mutation primitive;
- worker and future scheduler code share one stable winner-selection rule; and
- the core defines namespaced checkpoint provenance metadata for the winning parent
  genome.

There is no active public `ClanRound`, controller advancement protocol, controller
checkpoint state, or worker-owned mutation authority.

## Governing state model

The active member genome is the controlled subset of that member's Tune
`Trial.config`.

At a completed generation, the future CBT Tune scheduler will:

1. associate each reported fitness with the reporting trial's active genome;
2. identify and verify the sole winner and checkpoint source;
3. attach the winning parent genome and source identities to Ray checkpoint metadata;
4. derive one child genome per target trial;
5. install those child genomes in the targets' Tune configurations;
6. assign the same winning training checkpoint to every target; and
7. persist mutation RNG and replay lineage in scheduler state.

The shared checkpoint carries model, optimizer history, and training progress. Its
metadata records which parent genome produced that continuation. It does not contain
or own the target-local child genomes.

## Current work

The next Milestone 3 implementation slices are:

1. implement and qualify a Ray-backed `make_cbt_controller()` factory and fitness
   collective;
2. implement the CBT Tune scheduler's complete-generation barrier, genome association,
   mutation, lineage, checkpoint metadata update, and checkpoint assignment;
3. implement Lightning DDP setup and winner-aware checkpoint persistence;
4. apply target `Trial.config` controlled values after optimizer restoration; and
5. prove at least two complete rounds through a real Tune and Lightning DDP path.

Each slice must be developed tests-first and preserve the ordinary Tune function shape:

```text
get assigned checkpoint
→ restore training continuation
→ apply current trial genome
→ train and evaluate
→ worker controller resolves whether this rank saves
→ report one optional checkpoint
→ scheduler annotates and redistributes the winner
```

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

- There is no active Ray-backed `make_cbt_controller()` factory.
- There is no active CBT Tune scheduler.
- There is no active Lightning DDP integration or winner-aware checkpoint path.
- Checkpoint metadata attachment is defined and unit-tested as a plain mapping but not
  yet qualified against Ray 2.56 checkpoint storage.
- There is no live optimizer-configuration application system.
- The version-sensitive Tune checkpoint-assignment seam still requires direct
  framework-contract qualification.
- Historical proof-of-concept code remains evidence only and must not be restored
  wholesale as architectural authority.
