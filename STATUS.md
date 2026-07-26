# ClanBasedTuning project status

Last updated: 2026-07-25

## Current position

The framework-alignment responsibility model, project decisions, milestone gate
system, and durable working-process documents are present and remain subject to
ordinary correction through their owning artifacts.

The framework-independent `ClanController` is the first accepted implementation
surface. Existing Ray/Lightning integration source and examples remain
proof-of-concept evidence rather than an accepted construction API.

## Current work

Milestone 2 is completing the framework-independent evolutionary controller.
Human review has accepted the responsibility boundary:

- Milestone 2 owns the independent population policy.
- Milestone 3 chooses and qualifies the Ray Tune invocation seam and completes the
  real Ray/Lightning/PyTorch workflow.

The controller contract, implementation, focused tests, and engineering reference
are complete. The remaining Milestone 2 review unit is the repeated synthetic pet
loop and Milestone 3 integration handoff.

## Active plan

The [Milestone 2 controller plan](docs/plans/milestone_2_controller.md) now has two
stable review units:

1. controller contract, implementation, focused tests, and engineering reference;
2. repeated synthetic demonstration and Milestone 3 handoff.

Tentative alternatives and framework notes are not project authority.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Milestone 2 controller plan](docs/plans/milestone_2_controller.md)
- [Controller lifecycle and reference](docs/controller/README.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

- The repeated synthetic demonstration and Milestone 3 handoff are not yet
  complete, so Milestone 2 is not closed.
- The Ray invocation path, Lightning lifecycle integration, checkpoint transfer,
  distributed reformation, and live optimizer application remain Milestone 3
  work.
- Existing integration classes and examples must not be presented as accepted
  public contracts until the owning milestone accepts and documents them.
