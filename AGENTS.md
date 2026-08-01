# Repository instructions for coding agents

For substantial work, begin with [`docs/README.md`](docs/README.md). Read the governing
[`docs/product_roadmap.md`](docs/product_roadmap.md), then the design, contract,
implementation, qualification, or plan that owns the change.

Use [`docs/llm/README.md`](docs/llm/README.md) for the standing engineering and writing
process. Apply [`docs/reviews/framework_native_review.md`](docs/reviews/framework_native_review.md)
when a change affects a meaningful framework boundary.

[`STATUS.md`](STATUS.md) records current repository state. It is not an instruction queue
and does not replace the user's current objective. [`docs/plan.md`](docs/plan.md) sequences
only the active implementation work and cannot change the roadmap or accepted contracts.

A pull request must perform one coherent reviewable task and leave a stable intermediate
state. Do not create repository files merely to ask a design question. Tentative reasoning
belongs in scratchwork; accepted corrections belong in the artifact that owns them.

Do not merge pull requests, modify CI/workflow files, or change product meaning without
explicit authorization.
