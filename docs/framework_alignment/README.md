# Framework-alignment research package

Status: accepted explanatory and evidence package with active corrections in owning artifacts  
Date: 2026-07-25  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This package supplies the framework research, evidence, accepted responsibility
model, and human review records used by the roadmap and milestone system. It does
not certify the current proof-of-concept implementation, define a public API, or
act as the active implementation plan.

Existing code, tests, and examples remain evidence only unless a later milestone
accepts them as product evidence.

## Reader path

1. Read the [product roadmap](../product_roadmap.md) for product meaning,
   development criteria, and milestone sequence.
2. Read the [research report](research_report.md) for the framework model and
   accepted responsibility allocation.
3. Read [project decisions](../decisions/project_decisions.md) for accepted
   cross-milestone choices.
4. Consult the [evidence ledger](evidence_ledger.md) for source observations,
   probes, inferences, alternatives, and open qualification questions.
5. Apply the [standing framework-native review](../reviews/framework_native_review.md).
6. Read the [milestone gate system](../milestones/README.md) and the active
   [Milestone 2 gate](../milestones/gates/milestone_2_evolutionary_subsystem.md).
7. Use the active [Milestone 2 controller plan](../plans/milestone_2_controller.md)
   only for work sequence inside that gate.
8. Consult the [acceptance record](review_record.md) for accepted human outcomes
   and the [review audit](review_audit.md) for rejected iterations and process
   failures.
9. Use the [LLM operating context](../llm/README.md) and root
   [`STATUS.md`](../../STATUS.md) for working process and current durable status.

## Artifact authority

| Artifact | Role | Unique job |
| --- | --- | --- |
| [Product roadmap](../product_roadmap.md) | Governing | Defines product meaning, development criteria, and cumulative milestones. |
| [Project decisions](../decisions/project_decisions.md) | Accepted decisional authority | Resolves durable cross-milestone technical choices left open by the roadmap. |
| [Research report](research_report.md) | Accepted explanatory basis | Explains the framework model and reasons behind accepted responsibility decisions. |
| [Evidence ledger](evidence_ledger.md) | Evidence record | Preserves sources, probes, inferences, alternatives, and open questions without assigning work. |
| [Framework-native review](../reviews/framework_native_review.md) | Standing technical review | Tests algorithmic fidelity, native ownership, narrow seams, and evidence. |
| [Milestone gates](../milestones/README.md) | Milestone contracts | State the result and evidence required at each roadmap milestone. |
| [Active plans](../plans/README.md) | Subordinate execution authority | Sequence work inside the active gate without adding acceptance criteria. |
| [Acceptance record](review_record.md) | Human decision record | Records accepted outcomes without becoming technical authority. |
| [Review audit](review_audit.md) | Audit history | Preserves rejected iterations and what failed without polluting acceptance status. |
| [LLM operating context](../llm/README.md) | Standing process | Routes contributors through engineering, writing, authority, and PR rules. |
| [`STATUS.md`](../../STATUS.md) | Shared project status | States the latest durable position without becoming a work queue or roadmap. |

Where artifacts differ, the roadmap governs product meaning and sequence;
accepted decisions govern the questions they resolve; direct evidence governs
claims about upstream behavior; gates govern milestone completion; accepted
designs govern component contracts; and active plans govern only execution order
inside the active gate.

## Current boundary

Milestone 2 develops the framework-independent evolutionary controller.
Milestone 3 chooses and qualifies the Ray Tune invocation seam and completes the
real Ray/Lightning/PyTorch workflow. No current documentation should present the
proof-of-concept integration API as an accepted public contract.
