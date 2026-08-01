# Framework-alignment review audit

Status: audit history; not project authority  
Last updated: 2026-07-25

## Purpose

This file preserves rejected iterations, review failures, and corrective lessons.
It explains how the documentation and engineering process failed without mixing
those failures into the acceptance record or the artifacts that define current
technical behavior.

Accepted outcomes are recorded in [`review_record.md`](review_record.md).
Technical corrections belong in their owning roadmap, decision, gate, design,
plan, source, test, or documentation artifact.

## Documentation-system iterations

### Initial framework-alignment package

**Result:** rejected for combining research findings, implementation constraints,
standing gates, and milestone planning into too few artifacts.

**Lesson:** separate artifacts by reader purpose. A gate cannot simultaneously
explain evidence, choose design, sequence implementation, and record review.

### First restructured package

**Result:** improved but rejected because the decision register still mixed
cross-milestone commitments, milestone obligations, and audit findings.

**Lesson:** decisions, gates, evidence, plans, and review history need distinct
primary homes.

### Accountable milestone-gate package

**Result:** accepted as a useful structural foundation but incomplete as a whole
milestone product.

**Lesson:** capability, tests, documentation, examples or scientific work,
evidence, review, and handoff must be considered without forcing every dimension
to become a large subsystem.

### Project-complete gate iteration

**Result:** rejected for responsibility leakage. Framework checkpoint,
pause/resume, trial restart, and experiment-restoration qualification were pulled
into the controller milestone because they were technically adjacent.

**Lesson:** derive milestone obligations from roadmap responsibility rather than a
catalog of concerns. Ordinary cumulative progress is not a recovery subsystem or
a reason to predesign later work.

### Full framework-alignment pass

**Result:** accepted after targeted corrections to P3, P4, and P7 while preserving
unaffected decisions.

**Lesson:** reopen only the clause contradicted by evidence; do not discard an
accepted authority system wholesale.

## Operating-context iteration

The first operating-context draft combined execution workflow and detailed
writing standards in one long manual.

**Result:** rejected in that form.

**Lesson:** keep the executable workflow concise and consult detailed standards
from the stage or defect that needs them. Targeted context loading must not become
an excuse to avoid reading the complete relevant system.

## Milestone 2 implementation review

### Pull request #11

**Result:** rejected despite passing CI.

The PR combined authority repair, process documentation, roadmap/status changes,
controller design, implementation, tests, examples, and public/internal
explanation across 25 files. Review found:

- the root README acted as a process and API document rather than dispatch;
- unaccepted public APIs were presented without explicit TODO status;
- tentative reasoning and integration notes were placed in authoritative files
  instead of scratchwork;
- the review record mixed acceptance status with failure history and inserted
  closure language;
- roadmap and status responsibilities were duplicated;
- the M2/M3 boundary still mixed controller policy with Ray invocation choice;
- controller documentation placed lifecycle boundaries too late;
- the example demonstrated isolated calls rather than repeated evolution;
- source documentation, names, ownership language, randomness, validation, and
  API reference were not clean enough for acceptance; and
- the PR was too large for a reasonable human review unit.

**Lesson:** CI success is necessary but not architectural acceptance. Perform the
contract, boundary, documentation, reduction, and source-order adversarial passes
before submission, then split work at stable review boundaries.

### Pull request #12

**Result:** rejected and closed unmerged.

The PR added one persistent scratch proposal solely to ask whether the M2/M3
responsibility correction should be made. It did not apply the change or leave a
useful self-contained repository state.

**Lesson:** a PR is a mergeable unit of work, not a communication substitute.
Discuss a design question directly; once accepted, apply it in the artifacts that
own it.

## Standing corrective rules

- Read the nearest documentation `README.md` before editing a subtree.
- Keep root README content to project dispatch, status routing, and explicit TODO
  surfaces.
- Keep tentative reasoning in scratchwork and accepted work sequence in a
  subordinate active plan.
- Keep acceptance decisions and rejection audit history separate.
- Do not move live status into the roadmap or technical process into the root
  README.
- Document lifecycle and ownership before detailed API syntax.
- Demonstrate a controller through repeated evolution, not only unit-shaped calls.
- Submit one coherent small-to-medium task per PR and leave a stable mergeable
  intermediate state.
