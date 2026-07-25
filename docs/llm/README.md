# LLM operating context

## Purpose

This directory contains durable working-process instructions for substantial
ClanBasedTuning work. It does not summarize the project, choose the current task,
or replace the roadmap, decisions, gates, designs, plans, code, tests, or human
review.

The objective is reliable transfer: a fresh contributor should be able to find
the governing material, understand the relevant system, and perform a named task
without reconstructing undocumented conversational habits.

## Start with the repository and local reader paths

1. Read the root [`AGENTS.md`](../../AGENTS.md).
2. Identify the requested task and the repository area it affects.
3. Read the nearest `README.md` for every documentation subtree you may edit.
4. Load the complete authority chain, current implementation, tests, consumers,
   and evidence needed to judge that task correctly.

Targeted context loading means excluding unrelated project areas. It does not
mean reading the minimum possible material or avoiding necessary system review.

For milestone work, read [`docs/milestones/README.md`](../milestones/README.md)
before any gate or plan. For framework-alignment work, enter through
[`docs/framework_alignment/README.md`](../framework_alignment/README.md).

## Choose the working process

- Use the [senior engineering workflow](senior_engineering_workflow.md) for
  substantial design, implementation, debugging, refactoring, and technical
  review.
- Use the [technical-writing workflow](technical_writing_workflow.md) for
  roadmaps, decisions, gates, designs, plans, reports, audits, READMEs, reference
  documentation, docstrings, and substantial technical explanations.
- Consult the [technical-writing standards](technical_writing_standards.md) from
  the writing workflow when a stage or defect requires detailed criteria.

Most governing designs and implementation PRs require both workflows. Technical
correctness does not excuse a broken reader path, and polished prose does not
repair an incorrect contract.

## Project authority

Use artifacts for their assigned jobs:

1. The [product roadmap](../product_roadmap.md) governs product meaning,
   development criteria, and milestone sequence.
2. Accepted [project decisions](../decisions/project_decisions.md) govern the
   cross-milestone questions they resolve unless a specific clause is reopened.
3. [Milestone gates](../milestones/README.md) state what must be true before a
   milestone closes.
4. Accepted designs define component contracts. Active plans sequence work only
   within the current gate and may not decide later milestones in advance.
5. Research and evidence support conclusions; they do not independently assign
   work or override accepted decisions.
6. Code and tests establish current behavior. Existing behavior is evidence, not
   automatic architectural authority.
7. Review records preserve accepted outcomes. Audit files preserve rejected
   iterations and failure history; neither substitutes for the owning artifact.
8. Scratchwork stores tentative research, alternatives, and reasoning that has
   not become project authority.

When artifacts disagree, identify their roles before editing. Correct the
artifact that owns the contradiction rather than patching the nearest file or
copying the same statement into several documents.

## Current work and status

[`STATUS.md`](../../STATUS.md) states the latest durable project position for
humans and tools. It may identify accepted work, the current review unit, the next
planned capability, blockers, and governing links.

`STATUS.md` is not an autonomous work queue, session handoff, scratchpad, or
substitute for live repository state. When the user names a task, that request
governs the current work. When a continuation request is genuinely ambiguous,
read status and live PR/branch state, then ask only for the missing task identity.

Update `STATUS.md` when durable project position changes materially. Do not copy
commit-by-commit progress, CI logs, speculative ideas, or private conversational
history into it.

## Documentation placement

Before adding or moving information, identify its reader and primary home:

- root README: project dispatch and explicit unaccepted/TODO surfaces;
- status: current durable position;
- roadmap: product direction and milestone sequence, not live status;
- decision: accepted cross-milestone choice;
- gate: completion result and evidence, not implementation design;
- design/reference: component contract, lifecycle, algorithms, and data model;
- plan: executable work sequence within the active gate;
- review record: accepted human outcomes;
- audit: rejected iterations and what failed;
- scratchwork: tentative reasoning and alternatives.

Do not force a newly discovered gap into an existing document merely because that
document is already being edited.

## Pull-request boundary

A pull request must perform one coherent small-to-medium task and leave a stable,
mergeable repository state. It may be an incremental step, but it must be useful
and internally complete at that step.

Do not use a PR, plan file, or scratch document merely to communicate a question
to the user. Discuss unresolved architecture before opening the PR. Split design,
implementation, integration, and unrelated authority repair when each can form a
stable review unit. Temporary test or lint exclusions must be identified as
temporary in status updates and removed before completion unless the repository
explicitly accepts them.

## Change control

Make ordinary in-scope improvements autonomously. Consult the user before
changing:

- the Clan Tuning mechanism or scientific interpretation;
- governing product meaning or milestone acceptance criteria;
- an accepted cross-milestone decision;
- state authority, recovery semantics, or public support claims;
- CI/workflow files, repository permissions, or release policy; or
- pull-request merge state.

Do not merge a pull request unless the user explicitly requests it.

## Before substantial action

A contributor should be able to state:

- the requested result and PR-sized review unit;
- the governing authority and owning artifacts;
- the relevant implementation boundary and consumers;
- the evidence required before choosing a design;
- which information belongs in authority, design, audit, or scratchwork; and
- how the unit will be tested and reviewed.

Gather missing evidence before committing to a direction. Ask the user only when
a required product, authority, or task decision cannot be resolved from the
request and repository.
