# LLM operating context

## Purpose

This directory contains durable working-process instructions for LLMs that
contribute to ClanBasedTuning. It does not summarize the project, identify the
current assignment, or replace the roadmap, decisions, gates, plans, code,
tests, or human review.

The objective is transferability: a fresh session should be able to discover the
relevant authority, understand how work is conducted, and begin a named task
without relying on undocumented conversational habits.

## Start by classifying the task

Before loading project material, identify the kind of work requested:

- implementation or refactoring;
- debugging or framework investigation;
- design or technical review;
- planning or milestone review;
- substantial technical writing;
- repository or pull-request operation; or
- a narrow informational question.

Read only the process modules relevant to that work:

- [Senior engineering workflow](senior_engineering_workflow.md) for substantial
  engineering, debugging, design, implementation, and review;
- [Business-technical writing workflow](technical_writing_workflow.md) for the
  executable writing loop used by roadmaps, decisions, designs, plans, reports,
  audits, READMEs, user guidance, reference documentation, and substantial
  technical explanations; and
- [Business-technical writing standards](technical_writing_standards.md) as the
  detailed evaluation reference consulted by the writing workflow when a stage
  or defect requires it.

For writing work, enter through the workflow. Do not preload the complete
standards file merely because writing is involved; consult the sections relevant
to the current workflow stage or defect.

Many tasks require both the engineering and writing processes. A design document
that governs implementation, for example, must survive the engineering workflow
and the technical-writing workflow, with standards consulted as needed.

## Discover project authority

Do not reconstruct intent from filenames, class names, the newest commit, or the
root README.

Use the repository's authority system:

1. The [product roadmap](../product_roadmap.md) governs product meaning,
   development criteria, and milestone sequence.
2. Accepted [project decisions](../decisions/project_decisions.md) govern the
   cross-milestone questions they resolve unless a specific clause is explicitly
   reopened.
3. [Milestone gates](../milestones/README.md) govern what must be demonstrated
   before a milestone closes.
4. Accepted designs and active plans govern implementation structure and work
   sequence within those higher contracts.
5. Research and evidence records support conclusions; they do not independently
   assign work or supersede decisions.
6. Code and tests establish current implementation behavior. Existing behavior
   is evidence, not automatic architectural authority.
7. Review records preserve audit history; they do not become technical decision
   sources.

When two artifacts disagree, identify their roles and authority before editing
one. Correct the artifact that owns the contradiction rather than patching the
nearest file.

## Discover current work without inventing intent

[`STATUS.md`](../../STATUS.md) is a shared, human-readable description of the
repository's latest durable position. It may identify recently completed work,
work currently under review, the next planned capability, blockers, and links to
governing material.

`STATUS.md` is not an autonomous work queue. Repository state cannot establish
what the user wants to do in the present conversation.

When the user names a task, use that task and load only the relevant status,
authority, plan, implementation, tests, and evidence. When the user asks to
continue earlier work without identifying it:

1. read `STATUS.md`;
2. inspect live branch, pull-request, issue, and CI state where relevant; and
3. ask the user which work should be resumed or whether the recorded continuation
   remains current.

Do not silently choose the newest milestone, plan, pull request, or unfinished
item.

## Maintain `STATUS.md` as shared documentation

Humans and LLMs maintain `STATUS.md` under the same writing standards. It must
read like normal project documentation, not like a machine scratchpad or a
message to a future model.

`STATUS.md` owns the durable project-level abstraction: what capability is
accepted, what capability is active, what capability comes next, what durable
blocker exists, and where the owning contracts live. It summarizes those
contracts without reproducing their subordinate design or execution details.

In particular:

- milestone gates own completion criteria;
- decisions own durable technical choices;
- plans own work-unit order, option analysis, and execution sequence;
- designs own component structure and detailed boundaries; and
- live GitHub state owns current commits, checks, and pull-request mechanics.

Do not copy those details into `STATUS.md` merely to make it locally complete.
Use a project-level statement and a descriptive link to the owning artifact. A
plan should usually be able to reorder work units, refine alternatives, or change
an internal seam without requiring a status edit. Update status only when the
project-level meaning exposed by that abstraction changes.

Update it when durable project position changes materially, such as:

- a milestone or major review passes, reopens, or changes scope;
- a governing decision is accepted, revised, or reopened;
- the active or next project capability changes;
- a durable blocker appears or is resolved; or
- an authoritative document moves or is replaced.

Do not update it for every commit, test run, conversation, speculative idea,
work-unit reorder, implementation alternative, or internal design refinement.
Live GitHub details should be linked or queried rather than copied exhaustively.

Write status in project terms. Avoid phrases such as:

- “the human said”;
- “last human update”;
- “the LLM should remember”;
- “continue where the previous model stopped”;
- private conversational history; or
- instructions addressed only to an agent.

A status section should state the project condition directly: what is accepted,
what is active, what is next, what is blocked, and where the governing material
lives.

Before changing `STATUS.md`, check the governing artifacts and live repository
state. After changing it, verify that:

- a human reader can understand the project position without knowing who wrote
  the file;
- each detail appears at the abstraction level owned by status; and
- an internal change to a linked plan or design would not make status stale unless
  the durable project position also changed.

## Change control

Make ordinary in-scope design improvements autonomously and report them. Consult
the user before changing:

- the Clan Tuning mechanism or scientific interpretation;
- roadmap scope, milestone meaning, or acceptance criteria;
- state authority, recovery semantics, or public support claims;
- an accepted cross-milestone decision;
- CI or workflow files;
- repository permissions or release policy; or
- pull-request merge state.

Accepted decisions remain governing by default. Concrete contradictory evidence
may justify reopening a specific clause; it does not make every surrounding
decision provisional.

Do not merge a pull request unless the user explicitly requests the merge.

## Before substantial action

A fresh contributor should be able to state:

- the requested task and expected result;
- the governing authority and owning artifact;
- the relevant implementation boundary and consumers;
- the evidence needed before choosing a design;
- which changes are ordinary and which require consultation; and
- how completion will be judged.

If one of these cannot be determined from the request and repository, gather the
missing evidence or ask the smallest necessary question before committing to a
direction.
