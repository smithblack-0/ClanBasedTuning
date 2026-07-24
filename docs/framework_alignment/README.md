# Framework-alignment research package

Status: proposed Milestone 1 package for human acceptance  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This package supplies the research and audit record required by Milestone 1 of
the [product roadmap](../product_roadmap.md). It supports review of the proposed
project decisions, standing framework-native review, milestone gate system, and
Milestone 2 execution plan.

The roadmap remains the governing project contract. The dated project decisions
progressively resolve choices it intentionally left open. The milestone gate
files assign completion obligations. This research package explains and audits
those choices; it does not replace them.

The package does not certify the current proof-of-concept implementation.
Existing code and tests are evidence only.

## Review path

1. Read the [research report](research_report.md) for the framework model and the
   reasoning behind the proposed decisions.
2. Review the [project decisions](../decisions/project_decisions.md) for the
   cross-milestone choices later work may rely on after acceptance.
3. Consult the [evidence ledger](evidence_ledger.md) where a decision needs
   source-level inspection.
4. Review the [standing framework-native review](../reviews/framework_native_review.md).
5. Review the complete [milestone gate system](../milestones/README.md), beginning
   with the [Milestone 1 closure gates](../milestones/gates/milestone_1_framework_alignment.md).
6. Review the [evolutionary-controller plan](../milestones/evolutionary_controller_plan.md)
   against the [Milestone 2 gates](../milestones/gates/milestone_2_evolutionary_subsystem.md).
7. Record acceptance and corrections in the
   [Milestone 1 human review record](review_record.md).

## Artifact authority

| Artifact | Authority | Unique job |
| --- | --- | --- |
| [Product roadmap](../product_roadmap.md) | Governing | Defines product meaning, development criteria, and cumulative milestones. |
| [Project decisions](../decisions/project_decisions.md) | Decisional after acceptance | Resolves dated cross-milestone technical choices left open by the roadmap. |
| [Framework-native review](../reviews/framework_native_review.md) | Standing contractual review after acceptance | Tests every meaningful boundary for algorithmic fidelity, native ownership, narrow seams, and evidence. |
| [Milestone gates](../milestones/README.md) | Milestone contractual after acceptance | State what each milestone must prove and where every deferral is owned. |
| [Research report](research_report.md) | Explanatory | Builds the framework model and explains why the proposed decisions follow. |
| [Evidence ledger](evidence_ledger.md) | Audit record | Preserves sources, probes, inference, alternatives, and named qualification obligations. |
| [Human review record](review_record.md) | Audit record | Records review outcomes without becoming a decision or gate source. |
| [Evolutionary-controller plan](../milestones/evolutionary_controller_plan.md) | Instructional | Sequences the work required to satisfy Milestone 2. |

Where artifacts differ, the roadmap governs product meaning; accepted dated
project decisions govern the questions they resolve; milestone gates govern
completion; and direct framework evidence governs claims about upstream
behavior.

## Current closure status

Milestone 1 is not yet accepted. It is ready for closure review only when every
item in the [Milestone 1 gate file](../milestones/gates/milestone_1_framework_alignment.md)
has evidence and human acceptance.

The package must not be described as complete merely because the files exist.
Human review may revise the decisions, gate ownership, evidence record, or next-
milestone plan.
