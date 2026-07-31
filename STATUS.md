# ClanBasedTuning project status

Last updated: 2026-07-31

## Current position

Milestone 1 established the accepted framework-alignment research, project decisions,
roadmap, milestone gates, and durable engineering process.

Milestone 2 established the framework-independent evolutionary subsystem:
`MutationSpec`, `ClanRound`, and `ClanController`.

Milestone 3 has an accepted system design and behavioral acceptance contract. The
first implementation slice corrects the controller lifecycle required by that design:
selection now closes the evaluated round without mutation, winner-derived controller
state is checkpointable, and next-round mutation can occur only after that state has
been restored into a receiving member.

The active implementation still contains no Ray Tune or Lightning DDP integration.
Historical integration code remains evidence in git history and is not an accepted
implementation foundation.

## Implemented Milestone 3 foundation

`ClanController.close_round()` now:

1. loads and validates one complete population;
2. selects and records the completed winner;
3. exposes whether the local process is preferred; and
4. leaves the current round unchanged for winner checkpointing.

The selected winner is included in `state_dict()`. After the winner state is restored,
`start_next_round()` preserves the receiving member ID, rebases a deterministic child
random stream from the winning lineage, retains the winning configuration for the
winning member, and mutates the other members from that same configuration.

The previous combined `advance()` operation is removed because it manufactured the
next population before the winner checkpoint existed.

## Current work

The next implementation work should connect the accepted round lifecycle to framework
boundaries in small TDD slices. The nearest unresolved pieces are:

- Ray collective exchange of one fitness value per live variant;
- winner-aware Lightning checkpoint persistence with all DDP ranks participating;
- Tune reporting of one real checkpoint and checkpoint assignment to every next trial;
- optimizer-value application after Lightning restores winner optimizer history; and
- a real multi-round Lightning DDP acceptance path.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
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
- The controller rebase rule is currently qualified only by focused deterministic
  tests; framework checkpoint restoration has not yet exercised it.
- The design's version-sensitive Tune checkpoint-assignment seam still requires direct
  framework-contract qualification against Ray 2.56.x.
