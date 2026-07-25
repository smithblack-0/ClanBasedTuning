# Milestone gate system

Status: accepted gate system; Milestone 2 active  
Date: 2026-07-24

## Purpose

Each gate states the complete project condition that must be true when its
roadmap milestone closes. A gate is an acceptance envelope over all solutions
that would make the milestone safe, useful, and sufficient for downstream work.

A gate may constrain observable behavior, ownership, failure semantics, tests,
documentation, examples, evidence, and handoff. It names a mechanism only when
the roadmap or an accepted project decision makes that mechanism invariant.

## Authority

The [product roadmap](../product_roadmap.md) governs product meaning,
development criteria, and milestone sequence. Accepted
[project decisions](../decisions/project_decisions.md) govern the
cross-milestone questions they resolve. A milestone gate translates those
authorities into closure conditions; it does not design the implementation.

When evidence shows that a roadmap or accepted-decision clause is wrong, reopen
that clause explicitly. Do not repair an awkward design or implementation by
quietly narrowing the gate.

## Gate, design, and execution separation

The documentation layers have different jobs:

1. The roadmap defines the capability and development sequence.
2. The gate contracts the broadest acceptable solution space for that
   capability.
3. An accepted design selects one solution inside that space.
4. An accepted plan may govern execution of that design within the active gate.
5. Implementation, tests, documentation, and examples produce closure evidence.

A design may be narrower than its gate because it chooses one acceptable
solution. A plan may be narrower than the design because it sequences the route
currently being executed. Neither may flow upward and become a gate requirement
merely because it is current.

A durable plan has authority only inside its declared active-milestone scope. It
may state what must now be built, checked, or sequenced given the accepted design
and current project state. It may not:

- narrow or reinterpret the active gate;
- prescribe acceptance conditions for later milestones;
- choose later framework seams, APIs, or implementation forms;
- become a second roadmap or cross-milestone contract; or
- remain authoritative after its gate closes unless explicitly reassigned.

When current work discovers a condition that a later milestone genuinely must
satisfy, propose that condition as a reviewed amendment to the later gate. Do
not preserve it as a forward promise hidden in the current plan.

`docs/milestones/` contains this system description and the gate files only.
Durable plans, when justified, must live in a clearly identified planning or
design location, state their active-milestone scope and authority, and link back
to the gate they serve. Exploratory scratch normally remains in the current
conversation, issue, or pull request. The project currently maintains no
persistent LLM scratch-planning directory; create one only after explicit human
approval and with unmistakable preliminary status.

## Gate review tests

Before accepting or revising a gate, apply all of these tests:

- **Alternate-solution test:** could materially different implementations satisfy
  the clause? If not, verify that the named mechanism is truly invariant.
- **Counterfactual-validity test:** could a solution fully satisfy the roadmap
  milestone while violating the clause? If yes, the clause is probably design
  leakage.
- **Plan-deletion test:** if every current plan and design vanished, would the
  gate still be complete and usable?
- **Downstream-sufficiency test:** if every clause is satisfied, can the next
  milestone rely on the resulting capability without knowing its implementation?
- **Upward-leakage test:** did a class, hook, schema, policy detail, work order, or
  current workaround enter the gate only because a plan uses it?
- **Unforeseen-failure test:** does the gate state the failure boundary strongly
  enough to reject unsafe outcomes without assuming the only ways failure can
  occur?

A failed test routes back to the gate contract or its governing authority. It is
not fixed by adding explanatory prose around the leaked design.

## Plan review tests

Before accepting or revising a durable plan, verify that:

- every planned result is necessary to satisfy the active gate or the accepted
  design chosen within it;
- the plan does not convert one implementation choice into a gate condition;
- the plan stops at the active gate boundary;
- any newly discovered future necessity is proposed to the owning future gate
  rather than asserted by the plan;
- deleting the plan would leave the roadmap, gates, and accepted decisions
  complete; and
- the plan can be retired when the gate closes without removing project truth.

## Activation rule

A later capability becomes enforceable when its roadmap milestone introduces
it. Earlier gates do not disclaim, predesign, or absorb that capability.

A requirement belongs in a milestone only when it is necessary to establish
that milestone's roadmap Outcome, Work, or Exit. Framework behavior may be
exercised as evidence without becoming a ClanBasedTuning-owned subsystem.

## Complete-project dimensions

Every milestone considers the dimensions relevant to its result:

1. **Capability and responsibility:** what becomes real and which owners provide
   its parts.
2. **Tests and direct evidence:** what must be exercised at the capability's
   natural boundary.
3. **Documentation:** what the relevant engineer, user, reviewer, or operator
   must understand or be able to do.
4. **Examples and scientific work:** what public-package behavior must become
   visible and interpretable.
5. **Project handoff:** what stable result downstream work may rely on.
6. **Closure evidence:** which artifacts and review results jointly establish
   completion.

A dimension may be small when the roadmap requires little of it. It may not pull
in responsibilities introduced only by a later milestone.

## Functional artifact rule

Artifact existence is not completion.

- A test must exercise the contract it claims, not unrelated framework behavior
  that merely occurs nearby.
- Documentation must enable its named reader task without reconstruction from
  source code, audit history, or private discussion.
- An example must use the evolving public implementation and expose the milestone
  behavior it claims to teach.
- Scientific work must report cost, limitations, and neutral or unfavorable
  results honestly. Closure never requires a favorable result.
- A handoff states the stable capability downstream work may rely on; it does not
  design the downstream implementation.

## Exceptional reassignment

If evidence shows that the roadmap places a required capability at the wrong
milestone or that the capability should leave project scope, the proposed change
must identify:

- the roadmap requirement being changed;
- the technical evidence;
- the destination milestone or explicit removal;
- the consequence for the current milestone result; and
- the human decision authorizing the change.

This process is for genuine roadmap or scope correction, not ordinary design
iteration.

## Gate files

1. [Milestone 1 — framework-alignment research](gates/milestone_1_framework_alignment.md) — complete
2. [Milestone 2 — evolutionary subsystem](gates/milestone_2_evolutionary_subsystem.md) — active
3. [Milestone 3 — integratable orchestration](gates/milestone_3_integratable_orchestration.md)
4. [Milestone 4 — usability](gates/milestone_4_usability.md)
5. [Milestone 5 — optimizer utility](gates/milestone_5_optimizer_utility.md)
6. [Milestone 6 — industry readiness](gates/milestone_6_industry.md)

## Closure rule

A milestone closes only after human review confirms every gate as satisfied by
cited evidence, explicitly revised through an accepted project decision, or
retained as a blocker. Unassigned work, contradictory status, shadow authority,
and artifacts that do not perform their stated function block closure.
