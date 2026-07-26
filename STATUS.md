# ClanBasedTuning project status

Last updated: 2026-07-26

## Current position

The framework-alignment responsibility model, project decisions, milestone gate
system, and durable working-process documents are present and remain subject to
ordinary correction through their owning artifacts.

Human review accepted the framework-independent `ClanController` responsibility
boundary and Milestone 2 lifecycle. The accepted policy is represented by the stacked
Milestone 2 review and its winner-checkpoint handoff correction.

Milestone 3 now has a complete proposed manual Ray Tune, Lightning, and PyTorch DDP
workflow in PR #17. The implementation and evidence remain review candidates until
human gate review accepts or corrects them.

## Current work

The active work is Milestone 3 closure review. The proposed result includes:

- process-local round-result exchange and controller invocation;
- synchronous native PBT checkpoint assignment with controller-owned selection;
- winner-only Lightning checkpoint serialization;
- common restore followed by receiving-member optimizer mutation;
- repeated real CPU/Gloo rounds with shared gradients and divergence;
- collective failure evidence;
- a public manual mechanics example;
- an initial Iris classification workload and neutral result;
- engineering documentation and tested limitations; and
- a proposed Milestone 4 usability handoff.

The gate-by-gate review record is
[`docs/milestones/reviews/milestone_3_review.md`](docs/milestones/reviews/milestone_3_review.md).

## Active review stack

1. PR #15 — accepted Milestone 2 per-process controller lifecycle;
2. PR #16 — winner discovery before checkpointing and mutation after common restore;
3. PR #17 — explicit Milestone 3 Ray/Lightning/PyTorch integration and closure evidence.

The PRs remain unmerged until explicitly requested.

## Governing references

- [Product roadmap](docs/product_roadmap.md)
- [Project decisions](docs/decisions/project_decisions.md)
- [Milestone gate system](docs/milestones/README.md)
- [Milestone 3 gate](docs/milestones/gates/milestone_3_integratable_orchestration.md)
- [Manual Milestone 3 workflow](docs/milestone_3_manual_workflow.md)
- [Milestone 3 closure review](docs/milestones/reviews/milestone_3_review.md)
- [Initial Iris experiment](docs/experiments/milestone_3_iris_initial.md)
- [Proposed Milestone 4 handoff](docs/milestone_3_to_4_handoff.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [LLM operating context](docs/llm/README.md)

## Tested support boundary

The proposed Milestone 3 evidence qualifies CPU execution, Gloo DDP, one Lightning
process per Tune trial, fixed concurrently resident populations, `reuse_actors=False`,
`max_failures=0`, and default one-optimizer/one-parameter-group reconciliation on
PyTorch 2.10.x, Lightning 2.6.x, and Ray Tune 2.56.x.

GPU, multi-node, FSDP, actor reuse, independent recovery, and arbitrary optimizer
layouts remain unqualified and must not be implied by the current review.
