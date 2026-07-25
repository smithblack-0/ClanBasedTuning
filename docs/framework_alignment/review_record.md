# Framework-alignment acceptance record

Status: accepted human decisions with current corrections applied in owning artifacts  
Last updated: 2026-07-25

## Purpose

This file records accepted human review outcomes. It does not preserve rejected
drafts, explain process failures, define technical contracts, or close milestones.
Accepted technical corrections must appear in the roadmap, decision, gate,
design, plan, code, test, or documentation artifact that owns them.

Rejected iterations and what went wrong are preserved separately in the
[framework-alignment review audit](review_audit.md).

## Accepted outcomes

### Framework responsibility model — accepted 2026-07-24

Human review accepted the framework-native responsibility baseline:

- PyTorch owns ordinary distributed execution and gradient collectives.
- Lightning owns training and validation cadence, optimizer construction,
  checkpoint contents and restoration, and data integration.
- Ray Tune owns trial execution, resources, checkpoint/configuration assignment,
  pause/resume, and experiment persistence in the Ray-backed path.
- ClanBasedTuning owns the Clan-specific population policy, optimizer-only
  variation, post-restore optimizer reconciliation, and collective validity.

The accepted corrections were applied to project decisions, the research report,
the evidence and standing-review system, and milestone gates.

### Project decisions — accepted with targeted revisions

P1, P2, P5, and P6 retained their accepted authority. Human review accepted the
revised P4 parent-selection allocation and the removal of milestone-specific
recovery assignments from P7 on 2026-07-24.

Human review revised P3 on 2026-07-25:

- Milestone 2 delivers the framework-independent population policy.
- Milestone 3 chooses and qualifies the Ray Tune invocation seam.

The accepted wording lives in
[`docs/decisions/project_decisions.md`](../decisions/project_decisions.md).

### Milestone responsibility sequence — accepted

- Milestone 2 ends with the independent controller, focused tests, engineering
  documentation, repeated synthetic demonstration, and integration handoff.
- Milestone 3 selects the Ray seam and proves the real Ray/Lightning/PyTorch
  workflow through repeated rounds.
- Later milestones add usability, optimizer utility, and industry support without
  creating competing implementations.

The gate files and active plan are the authority for exact milestone obligations
and work sequence.

### Durable working process — retained with corrections

The repository retains a durable engineering workflow, technical-writing workflow,
authority reader path, shared status file, and agent entry point. The current
versions require sufficient system review, local README discovery, correct
information homes, and self-contained mergeable pull requests.

These process documents guide work; they do not determine product meaning or the
current user objective.

## Current authoritative reader path

- [Product roadmap](../product_roadmap.md)
- [Project decisions](../decisions/project_decisions.md)
- [Milestone gate system](../milestones/README.md)
- [Milestone 2 controller plan](../plans/milestone_2_controller.md)
- [Framework-alignment research package](README.md)
- [LLM operating context](../llm/README.md)
- [Shared project status](../../STATUS.md)

This record contains no milestone-closure declaration. Closure is determined by
the relevant gate and explicit human review of its evidence.
