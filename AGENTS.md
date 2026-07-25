# Repository instructions for coding agents

For substantial engineering, design, review, or documentation work, read
[`docs/llm/README.md`](docs/llm/README.md) before acting.

Before editing a documentation subtree, read its nearest `README.md`. In
particular, read [`docs/milestones/README.md`](docs/milestones/README.md) before
editing milestone gates or plans.

[`STATUS.md`](STATUS.md) is shared project documentation written for humans and
tools. It describes the repository's latest durable position, but it is not an
instruction queue and does not establish the user's current objective.

A pull request must be a self-contained, mergeable increment that performs one
coherent task and leaves the repository in a stable state. Do not create a PR or
persistent repository file solely to ask the user a design question. Preliminary
reasoning belongs in scratchwork while it is useful; accepted decisions must be
applied in the artifacts that own them.

Follow the authority, change-control, engineering, and writing rules linked from
`docs/llm/README.md`. Do not merge pull requests, modify CI/workflow files, or
change governing product meaning without explicit authorization.
