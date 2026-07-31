# ClanBasedTuning project status

Last updated: 2026-07-31

## Current position

Milestone 1 established the accepted framework-alignment research, project decisions,
roadmap, milestone gates, and durable engineering process.

Milestone 2 established the framework-independent evolutionary subsystem:
`MutationSpec`, `ClanRound`, and `ClanController`, with focused tests and controller
documentation.

Milestone 3 now has an accepted system design and behavioral acceptance contract. The
design establishes the complete round lifecycle, the responsibility split between CBT,
Ray Tune, and Lightning DDP, the winner-only checkpoint path, and the framework seams
that implementation must qualify.

The active implementation surface still contains only the accepted Milestone 1 and
Milestone 2 products. Earlier Ray, Lightning, DDP, checkpoint, optimizer-application,
factory, framework-contract, and end-to-end example implementations remain available
through git history only and are not an accepted implementation foundation.

## Current work

The next work is to decompose the Milestone 3 design into small implementation slices
and executable contracts.

The first slices must preserve the designed lifecycle:

1. load the preferred continuation;
2. restore and rebase the preferred CBT controller state;
3. derive and apply member-local optimizer values;
4. train through Lightning DDP;
5. compare the complete fitness population through a Ray collective;
6. persist one preferred Lightning checkpoint;
7. report and transfer it through Tune; and
8. load it into the complete next population.

The current Milestone 2 controller lifecycle must be revised so selection and
checkpointing close the current round before rebase and mutation manufacture the next
round. Its accepted selection, mutation, bounds, and deterministic-state algorithms
remain the foundation for that correction.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Milestone 3 gate](docs/milestones/gates/milestone_3_integratable_orchestration.md)
- [Controller lifecycle and reference](docs/controller/README.md)
- [Milestone 3 system design](docs/design/README.md)
- [Behavioral test contracts](docs/design/behavioral_test_contracts.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

- There is no active Ray Tune invocation path.
- There is no active Lightning DDP integration or winner-aware checkpoint path.
- There is no Ray fitness collective integration.
- There is no live optimizer-configuration application system.
- The controller close/select/checkpoint versus restore/rebase/mutate lifecycle split is
  not yet implemented.
- The design's version-sensitive Tune checkpoint-assignment seam still requires direct
  framework-contract qualification against Ray 2.56.x.
- Historical proof-of-concept code must not be copied forward wholesale or treated as
  accepted merely because it once passed tests.
