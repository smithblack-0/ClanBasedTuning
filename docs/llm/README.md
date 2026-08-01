# Working process

This directory contains standing process instructions for substantial
ClanBasedTuning engineering and writing. It does not define product meaning,
architecture, current behavior, or the active task.

## Start here

1. Read root [`AGENTS.md`](../../AGENTS.md).
2. Read the documentation index at [`docs/README.md`](../README.md).
3. Identify the artifact that owns the requested change.
4. Read the relevant source, tests, consumers, and evidence before editing.

Use:

- [`senior_engineering_workflow.md`](senior_engineering_workflow.md) for design,
  implementation, debugging, refactoring, and technical review;
- [`technical_writing_workflow.md`](technical_writing_workflow.md) for substantial
  technical documentation; and
- [`technical_writing_standards.md`](technical_writing_standards.md) as the detailed
  writing criteria used by that workflow.

Apply the standing
[framework-native review](../reviews/framework_native_review.md) whenever work changes a
meaningful PyTorch, Lightning, or Ray boundary.

## Authority

- [`product_roadmap.md`](../product_roadmap.md) governs product meaning and stable
  development criteria.
- Accepted behavioral and ownership contracts govern the behavior they state.
- Accepted designs allocate current system responsibility while leaving identified
  implementation choices open.
- Implementation decisions choose a replaceable mechanism.
- Qualification records bound support claims.
- [`plan.md`](../plan.md) sequences only current work.
- Code and tests establish current executable behavior.
- [`STATUS.md`](../../STATUS.md) records durable current state, not the user's task.
- Archive and scratchwork are not active authority.

When artifacts disagree, determine which one owns the disputed fact. Correct that
artifact rather than copying another summary into every neighboring file.

## Pull-request boundary

A pull request must perform one coherent reviewable task and leave a stable intermediate
state. Discuss unresolved architecture before implementation rather than using a PR as a
question. Keep proposals in scratchwork only while they remain tentative, and apply
accepted corrections to the artifact that owns them.

Do not merge pull requests, modify CI/workflow files, or change product meaning, state
authority, recovery semantics, or public support claims without explicit authorization.
