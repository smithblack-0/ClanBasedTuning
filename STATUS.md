# ClanBasedTuning project status

Last updated: 2026-07-27

## Current position

Milestone 1 established the accepted framework-alignment research, project decisions,
roadmap, milestone gates, and durable engineering process.

Milestone 2 established the accepted framework-independent evolutionary subsystem:
`MutationSpec`, `ClanRound`, and `ClanController`, with focused tests and controller
documentation.

The active repository surface has been reset to those accepted Milestone 1 and
Milestone 2 products. Earlier Ray, Lightning, DDP, checkpoint, optimizer-application,
factory, framework-contract, and end-to-end example implementations have been removed
from the active tree. They remain available through git history only and are not an
accepted foundation for later work.

## Current work

Milestone 3 is paused while its integration design is reconsidered from the clean
Milestone 1 and Milestone 2 boundary. No active Ray or Lightning implementation is
currently accepted.

Future Milestone 3 work must begin from the accepted controller and framework ownership
contracts, introduce one reviewable improvement at a time, and may revise earlier
increments when new framework evidence changes the design.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Milestone 3 gate](docs/milestones/gates/milestone_3_integratable_orchestration.md)
- [Controller lifecycle and reference](docs/controller/README.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

- There is no active Ray Tune invocation path.
- There is no active Lightning lifecycle or checkpoint integration.
- There is no package-managed DDP, model-wrapping, or distributed-data setup.
- There is no live optimizer-configuration application system.
- Historical proof-of-concept code must not be imported, copied forward wholesale, or
  treated as an accepted design merely because it once passed tests.
