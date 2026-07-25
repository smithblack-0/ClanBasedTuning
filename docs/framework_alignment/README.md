# Framework-alignment research package

Status: accepted; Milestone 1 closed  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This package supplies the research, decision, evidence, standing-review,
milestone-gate, and next-milestone planning material produced by Milestone 1 of
the [product roadmap](../product_roadmap.md).

The roadmap remains the governing project contract. Human review accepted the
framework-alignment package and the later durable operating-context extension on
2026-07-24. Milestone 1 is closed.

The package does not certify the current proof-of-concept implementation.
Existing code, tests, and examples remain evidence only unless a later milestone
explicitly accepts them as product evidence.

When Milestone 2 began, a narrow responsibility correction separated the
independent controller from its later Ray integration. Milestone 2 now defines
and delivers the controller; Milestone 3 chooses and implements the Ray invocation
form. The historical framework evidence remains relevant when that integration
work activates.

## Review path

1. Read the [product roadmap](../product_roadmap.md) for the governing mechanism,
   development criteria, and milestone sequence.
2. Read the [research report](research_report.md) for the framework model and the
   reasons behind the accepted framework-alignment decisions.
3. Review the [project decisions](../decisions/project_decisions.md) for the
   accepted cross-milestone constraints, including the corrected P3 boundary.
4. Consult the [evidence ledger](evidence_ledger.md) for source observations,
   probes, inferences, alternatives, and unresolved qualification questions.
5. Apply the accepted [standing framework-native review](../reviews/framework_native_review.md).
6. Use the [milestone gate system](../milestones/README.md).
7. Review the [LLM operating context](../llm/README.md) and shared
   [`STATUS.md`](../../STATUS.md).
8. Execute the accepted
   [evolutionary-controller plan](../milestones/evolutionary_controller_plan.md)
   against the [Milestone 2 gate](../milestones/gates/milestone_2_evolutionary_subsystem.md).
9. Consult the [Milestone 1 human review record](review_record.md) for acceptance,
   closure, and the later Milestone 2 boundary correction.

## Artifact authority

| Artifact | Authority | Unique job |
| --- | --- | --- |
| [Product roadmap](../product_roadmap.md) | Governing | Defines product meaning, development criteria, and cumulative milestones. |
| [Project decisions](../decisions/project_decisions.md) | Accepted decisional authority | Resolves durable cross-milestone technical choices left open by the roadmap. |
| [Research report](research_report.md) | Accepted explanatory basis | Builds the framework model and explains the accepted framework conclusions. |
| [Evidence ledger](evidence_ledger.md) | Accepted audit record | Preserves source observations, probes, inference, alternatives, and open questions without assigning current work. |
| [Framework-native review](../reviews/framework_native_review.md) | Accepted standing review | Tests meaningful boundaries for algorithmic fidelity, native ownership, narrow seams, and evidence. |
| [Milestone gates](../milestones/README.md) | Milestone contracts | State the cumulative project result and evidence that become enforceable at each roadmap milestone. |
| [LLM operating context](../llm/README.md) | Accepted standing process | Transfers the engineering workflow, technical-writing workflow and standards, authority discovery, change control, and status maintenance. |
| [`STATUS.md`](../../STATUS.md) | Shared project status | States the latest durable project position at project abstraction level without determining current user intent. |
| [Evolutionary-controller plan](../milestones/evolutionary_controller_plan.md) | Active Milestone 2 execution plan | Sequences controller work without designing the Ray adapter or replacing the gate. |
| [Human review record](review_record.md) | Audit record | Records review outcomes without becoming a technical decision or gate source. |

Where artifacts differ, the roadmap governs product meaning and milestone
sequence. Accepted decisions govern the questions they resolve. Direct framework
evidence governs claims about upstream behavior. Milestone gates govern
completion, and active plans govern execution sequence without changing those
contracts.

## Closure status

Milestone 1 is closed. Milestone 2 is active and produces the independently
invokable controller. Selection and qualification of the Ray invocation seam
activate in Milestone 3.
