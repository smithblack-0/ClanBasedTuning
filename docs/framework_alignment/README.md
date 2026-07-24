# Framework-alignment research package

Status: proposed Milestone 1 package for human acceptance  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This package completes the framework-alignment work required by Milestone 1 of
the [product roadmap](../product_roadmap.md). It gives reviewers an auditable
path from framework research to proposed decisions, a standing native-design
review, and an actionable plan for the evolutionary subsystem.

The roadmap remains the governing project contract. These later, dated
artifacts progressively resolve framework and implementation choices that the
roadmap intentionally left open; they do not replace its product meaning,
development criteria, or milestone sequence.

The package does not certify the current proof-of-concept implementation.
Existing source and tests are evidence only. A current class or helper survives
only when later design and verification show that its responsibility still
belongs.

## Reader paths

### Review Milestone 1

1. Read the [research report](research_report.md) for the overall framework
   model and the reasoning behind the proposed decisions.
2. Review the [decision register](decision_register.md) for the choices that
   later work may treat as settled after acceptance.
3. Consult the [evidence ledger](evidence_ledger.md) where a decision needs
   source-level inspection.
4. Apply the [framework-native engineering review](framework_native_review.md)
   as the final standing go/no-go test.
5. Review the [evolutionary-controller plan](../milestones/evolutionary_controller_plan.md)
   to confirm that the next milestone is actionable.

### Begin the evolutionary subsystem

1. Start with the [decision register](decision_register.md).
2. Use the [framework-native engineering review](framework_native_review.md)
   throughout design and implementation.
3. Execute the [evolutionary-controller plan](../milestones/evolutionary_controller_plan.md).
4. Consult the evidence ledger only for the framework seams used by the current
   work unit.

### Prepare later Lightning integration

Use the [integration research backlog](integration_research_backlog.md). It
preserves questions about Lightning, DDP, checkpointing, data, precision,
resources, and recovery without turning preliminary integration strategy into
controller requirements or permanent project gates.

## Artifact authority

| Artifact | Authority | Unique job |
| --- | --- | --- |
| [Product roadmap](../product_roadmap.md) | Governing | Defines product meaning, development criteria, and cumulative milestones. |
| [Research report](research_report.md) | Explanatory | Builds the framework model and explains why the proposed decisions follow. |
| [Decision register](decision_register.md) | Decisional after acceptance | States the framework-alignment choices later work may rely on. |
| [Evidence ledger](evidence_ledger.md) | Referential | Traces material claims to upstream source, probes, inference, and remaining qualification. |
| [Framework-native engineering review](framework_native_review.md) | Standing contractual review after acceptance | Tests later work for algorithmic fidelity, native ownership, narrow custom seams, and support evidence. |
| [Integration research backlog](integration_research_backlog.md) | Advisory | Preserves later integration questions and preliminary directions without fixing their design. |
| [Evolutionary-controller plan](../milestones/evolutionary_controller_plan.md) | Instructional | Sequences the next milestone and owns its detailed completion criteria. |

Where artifacts differ, the roadmap governs product meaning, accepted dated
decisions govern the questions they resolve, and direct framework evidence
governs claims about upstream behavior. Research directions and backlog entries
remain advisory until accepted by their owning decision or design.

## Milestone 1 acceptance

Milestone 1 is ready to close when human review has:

- accepted or corrected the proposed decisions;
- accepted the standing framework-native review;
- found the evidence path sufficient to inspect the material reasoning;
- confirmed that unresolved questions are visible and assigned to the
  milestone that must answer them;
- accepted the evolutionary-controller plan as an actionable implementation
  route.

Executable qualification continues in the milestone that depends on each
framework seam. Milestone 1 establishes the evidence-backed basis and
responsibility structure; it does not pre-implement the controller or the later
Lightning integration.
