# Framework-alignment research package

Status: accepted framework-alignment package; Milestone 1 closure extension under review  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This package supplies the research, decision, evidence, standing-review,
milestone-gate, and next-milestone planning material required by Milestone 1 of
the [product roadmap](../product_roadmap.md).

The roadmap remains the governing project contract. The documentation structure
introduced by the merged package was accepted preliminarily. The subsequent
alignment pass revised P3, P4, and the allocation portion of P7 while preserving
the authority of unaffected accepted decisions. Human review accepted the
framework-alignment package on 2026-07-24.

Milestone 1 was then reopened narrowly to add durable operating context for new
contributors and fresh LLM sessions. That extension does not reopen the accepted
framework conclusions or project decisions.

The package does not certify the current proof-of-concept implementation.
Existing code, tests, and examples remain evidence only unless a later milestone
explicitly accepts them as product evidence.

## Review path

1. Read the [product roadmap](../product_roadmap.md) for the governing mechanism,
   development criteria, and milestone sequence.
2. Read the [research report](research_report.md) for the framework model and the
   reasons behind the accepted decision corrections.
3. Review the [project decisions](../decisions/project_decisions.md) for the
   accepted cross-milestone constraints.
4. Consult the [evidence ledger](evidence_ledger.md) for source observations,
   probes, inferences, alternatives, and unresolved qualification questions.
5. Apply the accepted [standing framework-native review](../reviews/framework_native_review.md).
6. Use the [milestone gate system](../milestones/README.md), including the final
   operating-context requirement in the
   [Milestone 1 gate](../milestones/gates/milestone_1_framework_alignment.md).
7. Review the [LLM operating context](../llm/README.md) and shared
   [`STATUS.md`](../../STATUS.md).
8. After final Milestone 1 closure, execute the accepted
   [evolutionary-controller plan](../milestones/evolutionary_controller_plan.md)
   against the [Milestone 2 gate](../milestones/gates/milestone_2_evolutionary_subsystem.md).
9. Consult the [Milestone 1 human review record](review_record.md) for acceptance,
   reopening, and final closure history.

## Artifact authority

| Artifact | Authority | Unique job |
| --- | --- | --- |
| [Product roadmap](../product_roadmap.md) | Governing | Defines product meaning, development criteria, and cumulative milestones. |
| [Project decisions](../decisions/project_decisions.md) | Accepted decisional authority | Resolves durable cross-milestone technical choices left open by the roadmap. |
| [Research report](research_report.md) | Accepted explanatory basis | Builds the framework model and explains the accepted decisions and corrections. |
| [Evidence ledger](evidence_ledger.md) | Accepted audit record | Preserves source observations, probes, inference, alternatives, and open questions without assigning milestone work. |
| [Framework-native review](../reviews/framework_native_review.md) | Accepted standing review | Tests meaningful boundaries for algorithmic fidelity, native ownership, narrow seams, and evidence. |
| [Milestone gates](../milestones/README.md) | Milestone contracts | State the cumulative project result and evidence that become enforceable at each roadmap milestone. |
| [LLM operating context](../llm/README.md) | Standing process material under final review | Transfers the engineering workflow, technical-writing workflow and standards, authority discovery, change control, and status maintenance. |
| [`STATUS.md`](../../STATUS.md) | Shared project status | States the latest durable project position for humans and tools without determining current user intent. |
| [Evolutionary-controller plan](../milestones/evolutionary_controller_plan.md) | Accepted Milestone 2 execution plan | Sequences Milestone 2 work without replacing its gate. |
| [Human review record](review_record.md) | Audit record | Records review outcomes without becoming a technical decision or gate source. |

Where artifacts differ, the roadmap governs product meaning and milestone
sequence. Accepted decisions govern the questions they resolve. Direct framework
evidence governs claims about upstream behavior. Milestone gates govern
completion, and active plans govern execution sequence without changing those
contracts.

## Closure status

The framework-alignment package passed human review on 2026-07-24. Milestone 1
remains open only for review of the durable LLM operating context, shared status
contract, and proof that a fresh contributor can discover both project authority
and working process without prior conversation.
