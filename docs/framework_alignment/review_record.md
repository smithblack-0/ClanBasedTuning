# Milestone 1 human review record

Status: Milestone 1 accepted and closed  
Date opened: 2026-07-24  
Framework alignment accepted: 2026-07-24  
Operating context accepted: 2026-07-24  
Milestone closed: 2026-07-24

## Purpose

This file records human review of the Milestone 1 package. It is an audit record,
not a technical decision source or milestone gate. Accepted corrections must be
made in the artifact that owns them.

## Review history

### Initial framework-alignment package

**Result:** rejected for restructuring.

The first package compressed research findings, implementation constraints,
standing gates, and milestone planning into too few artifacts. The main gate
attempted to explain, plan, and review implementation at once.

**Correction:** separate artifacts by reader purpose and create a short standing
framework-native review.

### First restructured package

**Result:** improved but not accepted.

The decision register still mixed cross-milestone commitments, milestone
completion obligations, and Milestone 1 audit findings. Later work used vague
timing and unclear authority.

**Correction:** separate project decisions, milestone gates, research evidence,
plans, and review history; create one gate file per roadmap milestone.

### Accountable milestone-gate package

**Result:** accepted preliminarily as a strong structural and technical
foundation, but Milestone 1 did not clear.

The document separation and many implementation gates were useful. The milestone
files did not consistently require the complete project result: tests were
embedded unevenly, documentation and examples were missing or compressed, and
project handoff was not consistently gated.

**Correction:** add explicit capability, tests, documentation, examples or
scientific work, evidence/review, and handoff dimensions.

Preliminary acceptance established a governing baseline; it did not prevent
later review from reopening a specific decision or assignment when a concrete
conflict was found.

### Project-complete gate iteration

**Result:** rejected for responsibility leakage.

The revision added the missing project products but distributed them from a
catalog of technical concerns rather than from each roadmap milestone's
responsibility. It pulled Ray checkpoint, pause/resume, trial restart, and
experiment-restoration qualification into the controller milestone; split normal
next-generation continuation from “recovery”; leaked restoration language into
usability and optimizer utility; and represented ordinary cumulative progress as
deferral.

**Correction:** restart from the responsibility-assignment stage of the writing
workflow. Derive milestone requirements from the roadmap Outcome, Work, and Exit;
apply the senior-engineering main-idea, ownership, boundary, and reduction passes;
then reuse prior text only when it survives those checks.

### Full framework-alignment pass

**Result:** accepted.

The alignment pass preserved accepted decisions by default and reopened only
clauses with demonstrated conflicts:

- P3's fixed PBT-subclass choice conflicted with the roadmap's then-explicit
  Milestone 2 subclass-versus-direct-controller decision.
- P4's assignment of source selection to Ray conflicted with the Clan
  controller's sole-parent policy responsibility.
- P7's three recovery scopes conflicted with the roadmap's controller,
  integration, and industry capability sequence.

P1, P2, P5, and P6 retained their accepted authority. Human review accepted the
revised P3 and P4 decisions and the removal of P7's milestone-specific recovery
allocation. The root README was excluded as stale routing.

Accepted corrections made in the owning artifacts:

- the project-decision file preserves the original P1–P7 structure and records
  the accepted revised P3, P4, and P7 language;
- the research report explains the accepted responsibility baseline and the
  reasons for the targeted corrections;
- the evidence ledger records observations, probes, inference, alternatives, and
  open questions without assigning milestone work;
- the standing review distinguishes milestone activation from component and
  framework ownership and clarifies exact test versions versus public
  compatibility claims;
- the milestone system uses roadmap activation rather than normal-progression
  deferral and preserves the roadmap rule that later milestones remain coarse;
- Milestone 2 stops at the independently invokable controller capability;
- Milestone 3 contains the first complete normal checkpoint-driven Clan workflow;
- Milestones 4 and 5 add usability and optimizer utility without creating new
  restoration contracts; and
- Milestone 6 contains the declared operational recovery and industry support
  envelope without precommitting to a final failure taxonomy.

### Operating-context reopening

**Result:** accepted after refactoring.

After accepting the framework-alignment package, review identified a remaining
transferability gap. The repository described the project model and milestone
work, but did not preserve enough of the working process that a fresh LLM session
or new contributor could reliably apply it without conversational apprenticeship.

The reopening did not revisit the accepted framework conclusions, decisions, or
milestone responsibility model.

Accepted additions:

- a stable root entry point for coding agents;
- a durable senior-engineering workflow;
- a concise backward-capable technical-writing workflow with separate detailed
  writing standards;
- authority-discovery, targeted-loading, change-control, and consultation rules;
- a root `STATUS.md` written as ordinary shared project documentation for humans
  and tools;
- explicit maintenance rules preventing `STATUS.md` from becoming an LLM-only
  scratchpad or autonomous work queue; and
- a cold-start standard under which ambiguous continuation requests are confirmed
  with the human rather than inferred from repository state.

The first technical-writing draft combined standards and execution in one long
manual. Review accepted the standards content but rejected the combined form
because the iterative workflow and backward edges were obscured by evaluation
detail. The correction separated the concise executable control loop from the
standards used to judge each stage.

### Milestone 2 activation correction

**Result:** accepted as a narrow responsibility correction.

When Milestone 2 began, review found that the controller-form language still
combined two distinct questions:

1. what the independently invokable Clan controller is; and
2. how Ray Tune later invokes that controller and executes its decision.

This caused framework-seam research to begin before the controller contract was
defined. Human review moved Ray invocation-form selection to Milestone 3 and
retained one Milestone 2 obligation: define an independent population policy that
is reasonably compatible with its expected consumer without importing that
consumer's runtime lifecycle.

The correction does not change the Clan mechanism, sole-parent authority, or
native framework-ownership decisions.

### Gate and plan authority correction

**Result:** the evolutionary-controller plan and its derived controller-design
proposal were rejected and deleted before implementation began.

Review discovered that `docs/milestones/evolutionary_controller_plan.md` had been
introduced beside the permanent milestone gate system and then treated as a
project authority. Temporary work-unit choices flowed upward into the Milestone 2
gate, project status, package index, review record, project decision detail, and
an unmerged roadmap revision. The plan also attempted to reason across Milestones
2 and 3 at once, blurring the difference between defining the accepted policy
capability and choosing its integration.

The underlying process defect was premature planning across abstraction and
milestone boundaries:

- a gate should contract the broadest acceptable solution space needed for safe
  downstream progress;
- an accepted design chooses one solution inside that gate;
- a durable plan may govern execution inside the active gate;
- a plan may not narrow the gate, become a second roadmap, or predesign later
  milestones; and
- a newly discovered future necessity must be proposed explicitly to the owning
  future gate rather than preserved as a forward promise in the current plan.

Corrective actions:

- delete the shadow evolutionary-controller plan;
- delete the controller-design proposal derived from it;
- reserve `docs/milestones/` for the gate-system README and gate files;
- re-derive Milestone 2 directly from the roadmap and accepted decisions;
- remove plan-derived design choices from gates and higher-level summaries;
- add alternate-solution, counterfactual-validity, plan-deletion,
  downstream-sufficiency, upward-leakage, and unforeseen-failure reviews; and
- retain no persistent LLM scratch-planning directory unless human review later
  establishes a need and explicit preliminary contract.

No source code, tests, dependencies, or workflow files had been changed under the
rejected plan.

Human review later approved `docs/llm/scratchwork/` as a preliminary,
non-authoritative home for framework research, source observations, option
fragments, tentative ideas, and unresolved questions. It is not a durable plan
and cannot assign work, narrow a gate, or predesign a later milestone.

### Milestone 2 controller design

**Result:** accepted for implementation; implementation and closure evidence remain
under review.

The accepted design is one stateless `ClanController` using plain Python input and
output. It initializes a complete optimizer-configuration population from required
defaults, selects the sole parent from one complete population, and emits the next
complete population using linear or logarithmic perturbations within declared
bounds. Explicit seeds provide reproducibility without controller persistence.

The design does not import Ray runtime objects, communicate between workers,
transfer checkpoints, apply live optimizer values, or choose the Milestone 3 Ray
invocation seam. It also avoids one-use public record classes where mappings and a
small tuple result express the contract directly.

## Final artifact status

| Artifact | Status | Review note |
| --- | --- | --- |
| Product roadmap | Governing; trusted | Defines product meaning and milestone sequence. Only the accepted M2/M3 responsibility correction may change its current-status wording. |
| Documentation structure | Corrected | Gates, accepted designs, scoped durable plans, scratchwork, status, evidence, and review history have distinct authority. `docs/milestones/` contains gates only. |
| Project decisions | Accepted | P3 assigns the independent controller to M2 and Ray integration choice to M3 without fixing the controller design. P4 and P7 remain accepted. |
| Research report | Accepted explanatory basis | Explains the framework model without becoming current execution authority. |
| Evidence ledger | Accepted audit record | Evidence and open questions are separated from gates and plans. |
| Framework-native review | Accepted standing review | Component ownership and milestone activation are distinguished. |
| Milestone gate system | Corrected and active | Gates contract complete acceptable results without importing active-plan choices. |
| Milestone 2 gate | Active | Defines the independent controller capability and reasonable compatibility without prescribing implementation. |
| Milestone 3–6 gates | Future milestone contracts | Remain outcome-level and must be rechecked for design leakage before activation. |
| Milestone 2 design | Accepted | The stateless plain-data `ClanController` design is implemented on the review branch. |
| Milestone 2 implementation | Under review | Source, focused tests, documentation, example, regression evidence, and human acceptance must agree before closure. |
| LLM scratchwork | Approved preliminary context | Preserves research and options without durable authority. |
| LLM operating context | Corrected | Transfers engineering and writing process, including gate/design/plan/scratchwork separation. |
| `STATUS.md` | Accepted shared status | Reports durable project abstractions without linking to a shadow plan. |

## Closure

Milestone 1 remains accepted and closed because its framework research,
responsibility decisions, gate system, and operating context remain valid after
the shadow-plan correction. Milestone 2 is active under the corrected broad gate.
Its controller design is accepted; implementation, regression evidence, and
Milestone 2 closure remain under review.
