# Milestone 1 gates — framework-alignment research

Status: working closure proposal under review

## Milestone result

The project has an accepted, evidence-backed basis for designing and implementing
ClanBasedTuning in a framework-native manner. The result is a coherent authority
chain, an inspectable research and evidence record, accepted cross-milestone
constraints, roadmap-derived milestone gates, and an actionable Milestone 2
plan.

## Authority and research gates

### M1.1 Status and authority are unambiguous

- The product roadmap is the governing contract.
- The preliminary acceptance of the documentation structure is distinguished
  from acceptance of its technical conclusions.
- Research, evidence, proposed decisions, milestone gates, plans, implementation
  evidence, and review history each have one stated role.
- No subordinate artifact describes an open conclusion as accepted.

### M1.2 The framework responsibility model is coherent

The research report explains the relevant PyTorch, Lightning, and Ray Tune
lifecycles and assigns each ordinary responsibility to its native owner. The
proposed ClanBasedTuning responsibilities follow from the Clan mechanism rather
than from the current proof of concept.

The report does not make a framework behavior into a ClanBasedTuning subsystem
or assign it to a milestone merely because the behavior was investigated.

### M1.3 Proposed project decisions are durable and roadmap-aligned

- Each proposed decision resolves a genuine cross-milestone question left open by
  the roadmap.
- Decisions do not contain milestone work plans, temporary support limits, or
  premature detailed design.
- ClanBasedTuning retains parent-selection policy while native frameworks retain
  trial, checkpoint, restoration, and distributed execution responsibilities.
- The Milestone 2 choice between a PBT specialization and a direct controller
  remains open for evidence-backed resolution inside that milestone.
- Collective population validity is separated from later operational recovery
  qualification.

## Evidence and test gates

### M1.4 Decisive framework claims are auditable

Every material framework claim identifies direct source, documentation, a focused
probe, or a clearly stated inference from those materials. Exact upstream
revisions provide research reproducibility without becoming exact package pins.

A reviewer can trace each proposed decision to supporting evidence, see the
alternative considered, and identify the remaining qualification question.

### M1.5 Evidence does not become hidden planning authority

The evidence ledger records observations, probes, inference, alternatives, and
open questions. It does not assign completion obligations; milestone gates and
active plans determine when an answer becomes necessary.

### M1.6 Current proof-of-concept evidence is scoped honestly

Current code, tests, and examples are identified by the mechanism they actually
demonstrate. Their record states which proposed conclusions they support and
which milestone or support claims they do not establish.

Milestone 1 does not require a new product example merely to manufacture one.
Its example obligation is to make existing evidence legible, reproducible where
practical, and correctly limited.

## Documentation-system gates

### M1.7 The reader path has one primary home for each question

The roadmap, package index, research report, evidence ledger, proposed decisions,
standing review, milestone gates, Milestone 2 plan, and human review record each
perform one complete assigned job without competing authority or unnecessary
repetition.

### M1.8 The standing engineering review is repeatedly usable

The standing review tests algorithmic fidelity, native ownership, demonstrated
framework gaps, narrow authority, and evidence. It routes detailed project
requirements to the gate where they become enforceable and component behavior to
the design artifact for its actual owner.

## Milestone-contract gates

### M1.9 Later gates derive from the roadmap at the appropriate precision

- Every roadmap milestone has a gate covering its capability, tests,
  documentation, examples or scientific work, evidence, and handoff.
- Normal cumulative progression is represented as activation, not deferral.
- Milestone 2 is detailed enough to execute next.
- Milestones 3 through 6 state required results, major boundaries, and expected
  evidence without pretending their final designs or test matrices are settled.

### M1.10 The Milestone 2 plan is actionable without predeciding its architecture

The plan:

- begins by comparing the narrow PBT-specialization and direct-controller options
  against real framework evidence;
- records and justifies the selected controller form before building around it;
- develops the controller implementation, focused and framework-contract tests,
  design and API documentation, inspectable example, and Milestone 3 handoff
  together;
- ends at an independently invokable population-decision subsystem;
- leaves complete Lightning/DDP training, checkpoint transition, data, resource,
  and distributed lifecycle integration to Milestone 3.

## Human acceptance gate

### M1.11 Human review accepts the complete package

Human review accepts or corrects the research conclusions, evidence
interpretation, proposed decisions, standing review, gate system, Milestone 2
plan, and proof-of-concept evidence classification. Any unresolved question
required to begin Milestone 2 remains an explicit blocker.

## Closure evidence

Milestone 1 closes with links to the accepted research report, evidence ledger,
project decisions, standing review, complete milestone gate system, Milestone 2
plan, scoped current-evidence record, and human review decision.
