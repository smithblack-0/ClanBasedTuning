# Milestone gate system

Status: active milestone-contract system  
Date: 2026-07-25

## Read this before editing gates or plans

Gate files state the cumulative result and evidence required to close a roadmap
milestone. They do not choose implementation structure, store tentative research,
or act as progress trackers.

Before editing a gate:

1. read the governing roadmap milestone;
2. read accepted decisions that constrain it;
3. identify the capability and evidence that become necessary at that milestone;
4. keep design choices in an accepted design and work sequence in an active plan;
5. keep tentative alternatives and unresolved reasoning in scratchwork.

A durable plan may direct work only within the active gate. It may record concrete
needs that later gates must satisfy, but it may not preselect how a later milestone
will implement them.

## Purpose

Each gate states the cumulative project result that must be true when its roadmap
milestone closes. A gate does not own framework behavior. It requires
ClanBasedTuning to deliver and demonstrate the project capability introduced by
the roadmap while respecting the governing component and framework ownership.

A milestone is not complete because its central code path runs. Its tests,
documentation, examples or scientific work, evidence, and handoff must establish
one coherent project result.

## Authority and detail

The [product roadmap](../product_roadmap.md) governs product meaning, development
criteria, and milestone sequence. Accepted project decisions govern the questions
they resolve. An explicitly reopened clause is unavailable as implementation
authority until human review accepts its replacement; reopening one clause does
not demote unrelated accepted decisions.

Only the active milestone and its accepted design or plan should be decomposed
into detailed work. Later gate files state the required result, major
responsibility boundaries, and expected evidence without pretending their final
design or test matrix is already known.

## Activation rule

Normal roadmap progression is not deferred work. A later capability becomes
enforceable when its milestone introduces it. Earlier gates do not disclaim,
transfer, or predesign that capability.

A requirement belongs in a milestone only when it is necessary to establish that
milestone's roadmap outcome, work, or exit. A framework behavior may be exercised
as part of that proof without becoming a ClanBasedTuning-owned subsystem.

## Complete-project dimensions

Every milestone considers the dimensions relevant to its result:

1. **Capability and responsibility:** what project capability becomes real and
   which owners provide its parts.
2. **Tests and direct evidence:** what must be exercised to prove that capability
   at its natural boundary.
3. **Documentation:** what the relevant engineer, user, reviewer, or operator
   must understand or be able to do.
4. **Examples and scientific work:** what package behavior must become visible
   and interpretable.
5. **Project integration and handoff:** what stable products later work may rely
   upon.
6. **Closure evidence:** which artifacts and review results jointly establish
   completion.

A dimension may be small when the roadmap requires little of it. It may not pull
in responsibilities introduced only by a later milestone.

## Functional artifact rule

Artifact existence is not completion.

- A test must exercise the ClanBasedTuning or integration contract it claims, not
  unrelated framework behavior that merely occurs nearby.
- Documentation must enable its named reader task without requiring
  reconstruction from source code, audit history, or private discussion.
- An example must use the evolving accepted implementation and expose the
  milestone behavior it claims to teach or demonstrate.
- Scientific work must report cost, limitations, and neutral or unfavorable
  results honestly. Closure never requires a favorable result.
- A handoff states the stable products the next milestone may rely on; it does not
  design that milestone in advance.

## Exceptional reassignment

If evidence shows that the roadmap places a required capability at the wrong
milestone or that the capability should leave project scope, the proposed change
must identify:

- the roadmap requirement being changed;
- the technical evidence;
- the destination milestone or explicit removal;
- the consequence for the current milestone result; and
- the human decision authorizing the change.

This process is for genuine roadmap or scope correction, not ordinary cumulative
development.

## Gate files

1. [Milestone 1 — framework-alignment research](gates/milestone_1_framework_alignment.md)
2. [Milestone 2 — evolutionary subsystem](gates/milestone_2_evolutionary_subsystem.md)
3. [Milestone 3 — integratable orchestration](gates/milestone_3_integratable_orchestration.md)
4. [Milestone 4 — usability](gates/milestone_4_usability.md)
5. [Milestone 5 — optimizer utility](gates/milestone_5_optimizer_utility.md)
6. [Milestone 6 — industry readiness](gates/milestone_6_industry.md)

Accepted active plans live in [`../plans/`](../plans/). Plans are subordinate to
the roadmap, decisions, and active gate.

## Closure rule

A milestone closes only after human review confirms every gate as satisfied by
cited evidence, explicitly revised through an accepted project decision, or
retained as a blocker. Unassigned work, vague future language, contradictory
status, and artifacts that do not perform their stated function block closure.
