# Milestone 1 gates — framework-alignment research

Status: proposed closure gates  
Date: 2026-07-24

## Milestone result

The project has an accepted, evidence-backed basis for designing
ClanBasedTuning in a framework-native manner. The result is a coherent authority
chain, not merely a collection of research notes.

## Gates

### M1.1 Governing authority is explicit

- The product roadmap remains the governing project contract.
- Later dated decisions resolve choices the roadmap left open without silently
  changing product meaning, milestone sequence, state authority, scientific
  meaning, or public support claims.
- The root README routes readers to the governing documents and labels the
  current implementation as proof-of-concept evidence.

### M1.2 Permanent decisions are separated from milestone obligations

- Accepted cross-milestone decisions have one dated project-decision file.
- Milestone completion requirements live only in the owning milestone gate file.
- Research history, source inspection, and provisional hypotheses do not appear
  as permanent decisions.
- No decision uses vague timing such as “later” or “initial support” where a
  milestone owner is required.

### M1.3 The framework research covers the required lifecycle

The research report and evidence ledger address, at minimum:

- population and trial ownership;
- round and evaluation ownership;
- evolutionary scheduling;
- checkpoint production, transfer, and restoration;
- optimizer-state inheritance and configuration reconciliation;
- DDP construction, initial synchronization, gradient reduction, and member
  divergence;
- training and fitness data semantics;
- population admission and resource residency;
- failure, planned completion, and experiment restoration.

Material uncertainties are assigned to an owning milestone gate rather than
left as an untracked “current direction.”

### M1.4 The audit record is inspectable

- Framework claims cite pinned upstream source or focused probe evidence.
- Observation, inference, accepted decision, and remaining qualification are
  distinguishable.
- Alternatives considered and reasons for rejection are preserved where they
  materially affect the selected architecture.
- Existing repository code and tests are treated as evidence, not as
  architectural authority.
- The evidence record does not act as an implementation plan or permanent gate
  file.

### M1.5 The standing review is usable

- The framework-native review is short enough to apply to every meaningful
  design or implementation boundary.
- It tests durable principles rather than milestone-specific implementation
  details.
- Detailed requirements route to the owning milestone gate and design.

### M1.6 Every roadmap milestone has an accountable gate file

- Milestones 2 through 6 each have a gate file.
- Obligations discovered during framework research are assigned to the milestone
  that must satisfy them.
- Every deferral names its destination, reason, later obligation, and required
  evidence.
- Future milestone gates may be refined later, but they already cover all known
  inherited work.

### M1.7 The next milestone is actionable

- The evolutionary-subsystem plan can be executed without reopening basic
  framework ownership on every work unit.
- The plan is auditable against the Milestone 2 gate file and the standing
  framework-native review.
- Private or version-sensitive Ray seams are treated as executable contract
  questions, not assumed architecture.
- The plan identifies how a failed framework assumption reopens the relevant
  project decision.

### M1.8 Human review has accepted the package

Human review has accepted or corrected:

- the project decisions;
- the framework-native review;
- the research conclusions and evidence path;
- the milestone gate system;
- the evolutionary-subsystem plan.

Any unresolved issue necessary to begin Milestone 2 remains a blocker rather
than an informal follow-up.

## Closure evidence

Milestone 1 closes with links to:

- accepted project decisions;
- the research report and evidence ledger;
- the standing framework-native review;
- all milestone gate files;
- the accepted Milestone 2 plan;
- the [human review record](../../framework_alignment/review_record.md).
