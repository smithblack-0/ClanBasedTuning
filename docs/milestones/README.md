# Milestone gates

Status: proposed milestone gate system  
Date: 2026-07-24

## Purpose

Each milestone has one gate file stating what complete project result must exist
before that milestone may close. A milestone is not complete because its central
code path runs. Capability, tests, documentation, examples, evidence, and
handoff must agree on one supported result.

The gate files own milestone obligations and named deferrals. They do not replace
the roadmap, permanent project decisions, design plans, or audit records.

Gate detail may increase as a milestone approaches. A later gate file may remain
coarser than the active milestone, but every responsibility deferred to it must
already be visible.

## Required gate dimensions

Every milestone gate file considers the following dimensions explicitly:

1. **Capability and design.** What behavior or project capability exists, which
   owners provide it, and which boundaries it must preserve.
2. **Tests.** Which focused, contract, integration, failure, restoration,
   accelerator, or scale tests prove the claimed behavior at the relevant
   boundary.
3. **Documentation.** Which reader must be able to understand, use, integrate,
   operate, or review the result, and which documents enable that work.
4. **Examples and scientific work.** Which public-package examples demonstrate
   the milestone, what observers can inspect, and how realism should increase
   with project capability.
5. **Evidence and review.** Which direct results justify closure and how human
   review distinguishes tests, observations, inferences, and decisions.
6. **Project integration and handoff.** How the result updates the repository,
   public claims, prior artifacts, and the next milestone's starting contract.
7. **Assigned deferrals and closure evidence.** What is intentionally excluded,
   who inherits it, and what final evidence closes the milestone.

A dimension may be small when the milestone genuinely requires little work in
that area. It may not be omitted merely because implementation work is easier to
specify.

## Functional artifact rule

Artifact existence is not gate satisfaction.

- A test must exercise the public or owning contract at the boundary it claims,
  including relevant failure ordering; a mocked approximation cannot certify an
  integration claim.
- Documentation must enable its named reader task without requiring the reader
  to reconstruct missing ownership, lifecycle, support, or failure information.
- An example must use the evolving public implementation, make the claimed
  behavior visible, and avoid private shortcuts that ordinary users cannot take.
- Scientific examples must report limitations and costs as well as favorable
  behavior; milestone closure never requires a favorable scientific result.
- A handoff must state what the next milestone may rely on and what it still owns.

## Gate files

1. [Milestone 1 — framework-alignment research](gates/milestone_1_framework_alignment.md)
2. [Milestone 2 — evolutionary subsystem](gates/milestone_2_evolutionary_subsystem.md)
3. [Milestone 3 — integratable orchestration](gates/milestone_3_integratable_orchestration.md)
4. [Milestone 4 — usability](gates/milestone_4_usability.md)
5. [Milestone 5 — optimizer utility](gates/milestone_5_optimizer_utility.md)
6. [Milestone 6 — industry readiness](gates/milestone_6_industry.md)

## Deferral rule

A milestone may defer work only when its gate file names:

- the destination milestone;
- why the current milestone does not require the capability;
- the exact obligation inherited by the destination milestone;
- the evidence required to close that obligation.

Phrases such as “later,” “not initially supported,” or “current direction” do
not constitute an assigned deferral.

## Closure rule

A milestone closes only after human review confirms every gate as:

- satisfied by cited evidence;
- explicitly not applicable under the accepted scope; or
- retained as a blocker.

Closure evidence must identify the implementation, test results, documentation,
examples, review record, and handoff that jointly establish the milestone result.
Unassigned work and vague future support claims block closure.
