# ClanBasedTuning project status

Last updated: 2026-07-24

## Current position

The framework-alignment design, responsibility model, project decisions, and
milestone gate system have passed human review. Milestone 1 is open only for the
final addition of durable operating context that lets a new contributor or fresh
LLM session work from the repository without relying on prior conversation.

The root README predates the accepted framework-alignment work and is not the
current project authority.

## Current work

The repository is adding:

- a stable entry point for coding agents;
- shared rules for discovering project authority and current work;
- the senior-engineering workflow used for substantial implementation and review;
- the business-technical writing workflow used for project documentation; and
- maintenance rules for this status file.

This operating-context extension is under review.

## Next planned milestone

Milestone 2 delivers an independently invokable evolutionary controller. Its
first work unit compares two implementation forms:

- a narrow specialization of Ray's synchronous PBT scheduler; and
- an independent controller with a thin Ray adapter.

The choice must be made from direct framework evidence before later controller
work depends on either form.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Framework-native engineering review](docs/reviews/framework_native_review.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Evolutionary-controller plan](docs/milestones/evolutionary_controller_plan.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

The existing package and tests remain proof-of-concept evidence. They do not by
themselves establish the accepted public architecture or satisfy later milestone
gates.
