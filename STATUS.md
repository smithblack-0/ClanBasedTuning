# ClanBasedTuning project status

Last updated: 2026-07-25

## Current position

Milestone 1 is complete. The repository has an accepted framework-alignment basis,
responsibility model, project decisions, milestone gate system, and durable operating
context for new contributors and fresh LLM sessions.

The existing integration package remains proof-of-concept evidence rather than the
accepted public architecture.

## Current work

Milestone 2 is active. The proposed `ClanController` implementation is under review.
It is a stateless, independently invokable population transform that initializes
optimizer configurations, selects the sole parent from a completed population, and
emits the next generation's optimizer configurations.

The implementation uses plain Python structures and explicit seeds. It does not own
Ray, Lightning, PyTorch, trials, checkpoints, distributed communication, live optimizer
application, or training lifecycle.

## Next capability

Milestone 3 manually integrates the accepted controller with Ray Tune, Lightning, and
PyTorch distributed training. It will choose and qualify the Ray invocation seam,
execute repeated sole-parent round transitions, and establish the complete manual
workflow.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Framework-native engineering review](docs/reviews/framework_native_review.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Clan controller design](docs/clan_controller.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

The controller supports finite real scalar optimizer fields with linear or logarithmic
geometry. Framework integration and realistic live-optimizer application remain later
milestone work. Milestone 2 is not complete until human review accepts the design,
implementation, evidence, documentation, and example together.
