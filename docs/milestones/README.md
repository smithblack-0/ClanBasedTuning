# Milestone gates

Status: proposed milestone gate system  
Date: 2026-07-24

## Purpose

Each milestone has one gate file stating what must be true before that milestone
may close. These files own milestone obligations and named deferrals. They do not
replace the roadmap, permanent project decisions, design plans, or audit records.

Gate detail may increase as a milestone approaches. A later gate file may remain
coarser than the active milestone, but every responsibility deferred to it must
already be visible.

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

Unassigned work and vague future support claims block closure.
