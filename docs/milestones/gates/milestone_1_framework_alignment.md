# Milestone 1 gates — framework-alignment research

Status: proposed closure gates  
Date: 2026-07-24

## Milestone result

The project has an accepted, evidence-backed basis for designing
ClanBasedTuning in a framework-native manner. The result is a coherent authority
chain, a complete project-level milestone system, and an actionable next plan—not
merely a collection of research notes or code constraints.

## Capability and authority gates

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

## Test and evidence gates

### M1.4 The audit record is inspectable

- Framework claims cite pinned upstream source, focused probe evidence, or both.
- Observation, inference, accepted decision, and remaining qualification are
  distinguishable.
- Alternatives considered and reasons for rejection are preserved where they
  materially affect the selected architecture.
- Existing repository code and tests are treated as evidence, not as
  architectural authority.
- The evidence record does not act as an implementation plan or permanent gate
  file.

### M1.5 Test obligations are assigned at the boundary that must prove them

- Every version-sensitive framework seam required by an accepted decision has
  either focused Milestone 1 probe evidence or a named executable contract gate
  in the milestone that will depend on it.
- The milestone gate system distinguishes policy unit tests, upstream contract
  tests, multi-framework integration tests, failure and restoration tests,
  accelerator qualification, and scale or operational tests.
- No proof-of-concept test is presented as certifying a final public contract it
  does not exercise.
- Future test requirements name the public or owning contract, relevant success
  and failure ordering, and the evidence needed to close the gate.

## Documentation gates

### M1.6 The documentation system performs distinct reader jobs

Human review confirms that:

- the roadmap governs product meaning and cumulative milestones;
- project decisions contain only cross-milestone technical commitments;
- the research report explains the framework model and reasoning;
- the evidence ledger preserves sources, probes, alternatives, and remaining
  qualification;
- the standing framework-native review is short enough for repeated use;
- milestone gate files own completion requirements;
- the Milestone 2 plan sequences work without replacing its gate file;
- the review record preserves feedback and acceptance without becoming technical
  authority.

The package index and root README provide a clear reader path through those
artifacts.

## Example and scientific-work gates

### M1.7 The project contracts an example progression

- Existing repository examples are inventoried and labeled according to what
  they actually prove; proof-of-concept examples do not imply accepted
  architecture or support.
- Milestone 2 requires a native Ray mechanics example using the public
  evolutionary controller.
- Milestone 3 requires real manual Lightning/DDP integration examples, including
  an initial scientifically meaningful workload rather than mocked control flow.
- Milestone 4 requires a short ordinary-user example and retains the lower-level
  manual composition as the advanced path.
- Milestone 5 requires realistic optimizer-layout examples and at least one
  interpretable optimizer-policy study using the public package.
- Milestone 6 requires scaled, operational, restoration, and model-sharding
  examples for every claimed industry support envelope.
- No milestone may use a cleaner private research implementation than the
  package being delivered to users.

## Project integration and handoff gates

### M1.8 Every roadmap milestone has an accountable project gate file

- Milestones 2 through 6 each gate capability, tests, documentation, examples,
  evidence, and handoff as well as assigned deferrals.
- Obligations discovered during framework research are assigned to the milestone
  that must satisfy them.
- Every deferral names its destination, reason, inherited obligation, and
  required evidence.
- Future milestone gates may be refined later, but they already cover all known
  inherited work.

### M1.9 The next milestone is actionable as a project milestone

- The evolutionary-subsystem plan can be executed without reopening basic
  framework ownership on every work unit.
- The plan is auditable against the complete Milestone 2 gate file and the
  standing framework-native review.
- Private or version-sensitive Ray seams are treated as executable contract
  questions, not assumed architecture.
- The plan includes implementation, tests, documentation, the native example,
  review, and handoff—not only controller code.
- The plan identifies how failed evidence reopens the relevant project decision
  or blocks milestone closure.

### M1.10 Human review has accepted the package

Human review has accepted or corrected:

- the project decisions;
- the framework-native review;
- the research conclusions and evidence path;
- the project-complete milestone gate system;
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
- the inventory and status of current examples and tests;
- the [human review record](../../framework_alignment/review_record.md).
