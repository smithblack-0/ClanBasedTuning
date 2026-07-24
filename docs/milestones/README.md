# Milestone gate system

Status: working rewrite for review

## Purpose

Each milestone gate states the complete cumulative project result that becomes enforceable at that point in the roadmap. Milestones do not own framework mechanisms. The gate requires ClanBasedTuning to deliver or demonstrate the project products introduced by that milestone while preserving the framework and component ownership established by accepted decisions.

A milestone is not complete because its central code path runs. Its implementation, tests, documentation, examples, evidence, and handoff must establish one coherent result.

## Activation rule

Normal roadmap progression is not deferred work. A later capability becomes enforceable when its milestone introduces it. Earlier gate files do not need to disclaim or transfer that responsibility.

A requirement belongs in a milestone when it is necessary to establish that milestone's stated outcome, work, or exit. A framework behavior may be exercised as part of that proof without becoming a ClanBasedTuning-owned subsystem.

## Required gate dimensions

Each gate considers:

1. **Capability and responsibility.** What project result becomes real and which accepted owners provide its parts.
2. **Tests and direct evidence.** What must be exercised to prove the claimed contract at its natural boundary.
3. **Documentation.** What the relevant engineer, user, reviewer, or operator must be able to understand or do.
4. **Examples and scientific work.** What public-package behavior must be visible at this stage of the project.
5. **Project integration and handoff.** What later work may rely upon after this milestone closes.
6. **Closure evidence.** Which artifacts and review results jointly establish completion.

A dimension may be small when the roadmap requires little of it. It may not absorb behavior introduced only by a later milestone.

## Functional artifact rule

Artifact existence is not completion.

- A test must exercise the ClanBasedTuning or integration contract it claims. It should not retest unrelated framework behavior merely because that behavior occurs nearby.
- Documentation must enable its named reader task without requiring reconstruction from source code or audit history.
- An example must use the evolving public implementation, make the milestone behavior visible, and avoid a cleaner private implementation.
- Scientific work must report limitations and unfavorable or neutral results honestly. Closure never requires a favorable result.
- A handoff must state the stable products the next milestone may rely on, not redesign the next milestone in advance.

## Exceptional reassignment

If evidence shows that an obligation expected by the current roadmap milestone cannot or should not be completed there, the proposed change must identify:

- the current requirement being changed;
- the technical reason;
- the destination milestone or explicit removal from project scope;
- the consequence for the current milestone result;
- the evidence and human decision authorizing the change.

This process is for genuine roadmap or scope changes, not ordinary cumulative development.

## Gate files

1. [Milestone 1 — framework-alignment research](gates/milestone_1_framework_alignment.md)
2. [Milestone 2 — evolutionary subsystem](gates/milestone_2_evolutionary_subsystem.md)
3. [Milestone 3 — integratable orchestration](gates/milestone_3_integratable_orchestration.md)
4. [Milestone 4 — usability](gates/milestone_4_usability.md)
5. [Milestone 5 — optimizer utility](gates/milestone_5_optimizer_utility.md)
6. [Milestone 6 — industry readiness](gates/milestone_6_industry.md)

## Closure rule

A milestone closes only after human review confirms that every gate is satisfied by cited evidence, explicitly revised through an accepted decision, or retained as a blocker. Unassigned work, vague future language, and artifacts that do not perform their stated function block closure.