# Framework-alignment research package

Status: open Milestone 1 package under human review  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This package supplies the research, proposed decisions, evidence, standing
review, milestone contracts, and next-milestone plan required by Milestone 1 of
the [product roadmap](../product_roadmap.md).

The roadmap is the governing project contract. The other artifacts remain open
until Milestone 1 human review accepts or corrects them. The merged documentation
structure was accepted preliminarily; that did not make every technical
conclusion inside it authoritative.

The package does not certify the current proof-of-concept implementation.
Existing code, tests, and examples are evidence only.

## Review path

1. Read the [product roadmap](../product_roadmap.md) for the governing mechanism,
   development criteria, and milestone sequence.
2. Read the [research report](research_report.md) for the proposed framework and
   responsibility model.
3. Review the [proposed project decisions](../decisions/project_decisions.md) for
   the durable cross-milestone choices the research recommends.
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

| Artifact | Current authority | Unique job |
| --- | --- | --- |
| [Product roadmap](../product_roadmap.md) | Governing | Defines product meaning, development criteria, and cumulative milestones. |
| [Project decisions](../decisions/project_decisions.md) | Proposed; decisional after acceptance | Resolves durable cross-milestone technical choices left open by the roadmap. |
| [Research report](research_report.md) | Explanatory proposal | Builds the framework model and explains why the proposed decisions follow. |
| [Evidence ledger](evidence_ledger.md) | Audit record | Preserves source observations, probes, inference, alternatives, and unresolved questions without assigning milestone work. |
| [Framework-native review](../reviews/framework_native_review.md) | Proposed standing review | Tests meaningful boundaries for algorithmic fidelity, native ownership, narrow seams, and evidence. |
| [Milestone gates](../milestones/README.md) | Proposed milestone contracts | State the cumulative project result and evidence that become enforceable at each roadmap milestone. |
| [Evolutionary-controller plan](../milestones/evolutionary_controller_plan.md) | Proposed instruction | Sequences Milestone 2 work without replacing its gate. |
| [Human review record](review_record.md) | Audit record | Records review outcomes without becoming a technical decision or gate source. |

Where artifacts differ, the roadmap governs product meaning and milestone
sequence. Direct framework evidence governs claims about upstream behavior.
Proposed decisions, gates, reviews, and plans remain revisable until human
acceptance gives them their stated authority.

## Current closure status

Milestone 1 remains open. It closes only when human review accepts or corrects
the proposed responsibility model, decisions, evidence interpretation, standing
review, milestone gates, and Milestone 2 plan, with every unresolved question
needed to begin Milestone 2 either answered or retained as an explicit blocker.

The package must not be described as complete merely because its files exist or
because its structural pull request was merged.
