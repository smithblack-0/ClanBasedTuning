# Framework-alignment research package

Status: Milestone 1 alignment review in progress  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This package supplies the research, decision, evidence, standing-review,
milestone-gate, and next-milestone planning material required by Milestone 1 of
the [product roadmap](../product_roadmap.md).

The roadmap remains the governing project contract. The documentation structure
introduced by the merged package was accepted preliminarily. Previously accepted
project decisions continue to govern unless a concrete conflict explicitly
reopens them. The current alignment pass has reopened only the P3 controller-form
clause, the P4 parent-selection authority clause, and the P7 milestone-specific
recovery allocation.

The package does not certify the current proof-of-concept implementation.
Existing code, tests, and examples are evidence only.

## Review path

1. Read the [product roadmap](../product_roadmap.md) for the governing mechanism,
   development criteria, and milestone sequence.
2. Read the [research report](research_report.md) for the framework model, the
   accepted responsibility baseline, and the reasons for the targeted
   reopenings.
3. Review the [project decisions](../decisions/project_decisions.md) for the
   accepted decisions, reopened clauses, and proposed replacements.
4. Consult the [evidence ledger](evidence_ledger.md) for source observations,
   probes, inferences, alternatives, and unresolved qualification questions.
5. Review the [standing framework-native review](../reviews/framework_native_review.md).
6. Review the [milestone gate system](../milestones/README.md), beginning with the
   [Milestone 1 closure gate](../milestones/gates/milestone_1_framework_alignment.md).
7. Review the [evolutionary-controller plan](../milestones/evolutionary_controller_plan.md)
   against the [Milestone 2 gate](../milestones/gates/milestone_2_evolutionary_subsystem.md).
8. Record acceptance, rejection, and required corrections in the
   [Milestone 1 human review record](review_record.md).

## Artifact authority

| Artifact | Authority | Unique job |
| --- | --- | --- |
| [Product roadmap](../product_roadmap.md) | Governing | Defines product meaning, development criteria, and cumulative milestones. |
| [Project decisions](../decisions/project_decisions.md) | Accepted except explicitly reopened clauses | Resolves durable cross-milestone technical choices; records the exact clauses reopened and their proposed replacements. |
| [Research report](research_report.md) | Explanatory | Builds the framework model and explains why accepted decisions survive or require targeted correction. |
| [Evidence ledger](evidence_ledger.md) | Audit record | Preserves source observations, probes, inference, alternatives, and open questions without assigning milestone work. |
| [Framework-native review](../reviews/framework_native_review.md) | Standing review material under Milestone 1 review | Tests meaningful boundaries for algorithmic fidelity, native ownership, narrow seams, and evidence. |
| [Milestone gates](../milestones/README.md) | Milestone contracts under Milestone 1 review | State the cumulative project result and evidence that become enforceable at each roadmap milestone. |
| [Evolutionary-controller plan](../milestones/evolutionary_controller_plan.md) | Next-milestone execution plan under review | Sequences Milestone 2 work without replacing its gate. |
| [Human review record](review_record.md) | Audit record | Records review outcomes without becoming a technical decision or gate source. |

Where artifacts differ, the roadmap governs product meaning and milestone
sequence. Accepted decisions govern the questions they resolve unless explicitly
reopened. Direct framework evidence governs claims about upstream behavior.
Milestone gates govern completion once accepted, and the active plan governs the
execution sequence without changing those contracts.

## Current closure status

Milestone 1 remains open. It closes only when human review:

- accepts or corrects the three reopened decision clauses;
- confirms that the research and evidence support the accepted responsibility
  model;
- accepts the standing review, milestone gates, and Milestone 2 plan;
- retains any unresolved question required to begin Milestone 2 as an explicit
  blocker.

The package must not be described as complete merely because its files exist or
because its structural pull request was merged.
