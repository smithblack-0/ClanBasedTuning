# ClanBasedTuning project status

Last updated: 2026-07-25

## Current position

The framework-alignment responsibility model, project decisions, milestone gate
system, and durable working-process documents are present and remain subject to
ordinary correction through their owning artifacts.

The current source and examples are proof-of-concept evidence. They do not define
an accepted architecture or stable public API.

## Current work

Milestone 2 is developing the framework-independent evolutionary controller.
Human review has accepted the responsibility boundary:

- Milestone 2 owns the independent population policy.
- Milestone 3 chooses and qualifies the Ray Tune invocation seam and completes the
  real Ray/Lightning/PyTorch workflow.

No Milestone 2 controller implementation is currently accepted. The next review
unit is the controller design and lifecycle contract described by the active plan.

## Active plan

The [Milestone 2 controller plan](docs/plans/milestone_2_controller.md) separates
work into stable review units:

1. controller design and lifecycle contract;
2. controller implementation and focused tests; and
3. repeated synthetic demonstration, engineering reference, and Milestone 3
   handoff.

Tentative alternatives and framework notes are not project authority.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Milestone 2 controller plan](docs/plans/milestone_2_controller.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

- The framework-independent controller design and implementation remain under
  development.
- The Ray invocation path, Lightning lifecycle integration, checkpoint transfer,
  distributed reformation, and live optimizer application remain Milestone 3
  work.
- Existing package classes and examples must not be presented as accepted public
  contracts until the owning milestone accepts and documents them.
