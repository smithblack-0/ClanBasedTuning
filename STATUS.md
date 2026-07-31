# ClanBasedTuning project status

Last updated: 2026-07-31

## Current position

Milestone 1 established the accepted framework-alignment research, project decisions,
roadmap, milestone gates, and durable engineering process.

Milestone 2 established the accepted framework-independent evolutionary subsystem:
`MutationSpec`, `ClanRound`, and `ClanController`, with focused tests and controller
documentation.

The active repository surface remains reset to those accepted Milestone 1 and
Milestone 2 products. Earlier Ray, Lightning, DDP, checkpoint, optimizer-application,
factory, framework-contract, and end-to-end example implementations remain available
through git history only and are not an accepted implementation foundation.

## Current work

A proposed whole-system design is under human review. It promotes the behavioral test
contracts into the design reader path and proposes responsibility, state-authority,
and lifecycle boundaries for composing the accepted controller with Ray Tune,
Lightning, and PyTorch DDP.

The design does not implement Milestone 3 or establish milestone completion. After
review, accepted corrections will be applied before the architecture is decomposed
into milestone-sized implementation work and executable TDD contracts.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Milestone 3 gate](docs/milestones/gates/milestone_3_integratable_orchestration.md)
- [Controller lifecycle and reference](docs/controller/README.md)
- [Proposed system design](docs/design/README.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

- There is no active Ray Tune invocation path.
- There is no active Lightning lifecycle or checkpoint integration.
- There is no package-managed DDP, model-wrapping, or distributed-data setup.
- There is no live optimizer-configuration application system.
- The proposed design has not yet been accepted or decomposed into implementation
  milestones.
- Historical proof-of-concept code must not be imported, copied forward wholesale, or
  treated as an accepted design merely because it once passed tests.
