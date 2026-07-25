# ClanBasedTuning project status

Last updated: 2026-07-24

## Current position

Milestone 1 is complete. The repository has an accepted framework-alignment
basis, responsibility model, project decisions, milestone gate system, and
durable operating context for new contributors and fresh LLM sessions.

The existing package and tests remain proof-of-concept evidence rather than the
accepted public architecture.

## Current work

Milestone 2 is active. It delivers an independently invokable evolutionary
controller that consumes one complete population result, selects the sole parent,
and produces the next generation's optimizer configurations and decision record.

The controller is designed for later native integration without owning Ray,
Lightning, PyTorch, trial, checkpoint, or training lifecycle behavior. The active
Milestone 2 plan owns the detailed work sequence.

## Next capability

Milestone 3 manually integrates the accepted controller with Ray Tune, Lightning,
and PyTorch distributed training. It will choose and qualify the Ray invocation
seam, execute repeated sole-parent round transitions, and establish the complete
manual workflow.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Framework-native engineering review](docs/reviews/framework_native_review.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)
- [Evolutionary-controller plan](docs/milestones/evolutionary_controller_plan.md)
- [LLM operating context](docs/llm/README.md)

## Known limitations

No controller implementation has yet satisfied the Milestone 2 contract. The
current Ray scheduler and integration code remain useful proof-of-concept evidence
but do not determine the controller design or the later Ray integration form.
