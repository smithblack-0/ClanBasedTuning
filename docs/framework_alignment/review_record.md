# Milestone 1 human review record

Status: review in progress  
Date opened: 2026-07-24

## Purpose

This file records human review of the Milestone 1 package. It is an audit record,
not a technical decision source or milestone gate. Accepted corrections must be
made in the artifact that owns them.

## Review history

### Initial framework-alignment package

**Result:** rejected for restructuring.

The first package compressed research findings, implementation constraints,
standing gates, and milestone planning into four files. In particular, the gate
file was too detailed for regular use and attempted to explain and plan the
implementation while acting as a go/no-go review.

**Correction:** rebuild the documentation around distinct reader purposes and
create a short standing framework-native review.

### First restructured package

**Result:** improved but not accepted.

The decision register still mixed three different lifecycles:

- cross-milestone project commitments;
- milestone completion obligations;
- Milestone 1 audit and process findings.

The integration backlog used phrases such as “current direction” and support was
deferred without assigning a milestone owner. Experiment restoration was
prematurely treated as a later custom recovery problem even though native Ray
checkpoint and experiment restoration may already provide the required behavior.

**Correction:**

- replace the mixed decision register with a cross-milestone project-decision
  file;
- create one gate file per roadmap milestone;
- move proof-of-concept handling into the Milestone 1 audit contract;
- replace vague deferrals with named destination, obligation, and evidence;
- require native Ray restoration qualification in Milestone 2, real Lightning
  restoration qualification in Milestone 3, and production recovery
  qualification in Milestone 6.

### Accountable milestone-gate package

**Result:** accepted as a strong structural and technical foundation, but
Milestone 1 did not clear.

The milestone gate files contained substantial implementation and framework
contracts, but did not consistently gate the complete project result. Tests were
embedded unevenly inside technical clauses, documentation and examples were
missing or compressed in several milestones, and the files did not consistently
require project integration or handoff evidence. As a result, a milestone could
plausibly pass because its central code worked even though the project lacked the
tests, documentation, examples, or scientific and user-facing products required
by the roadmap.

**Correction:**

- define required milestone dimensions for capability, tests, documentation,
  examples and scientific work, evidence and review, project handoff, deferrals,
  and closure;
- preserve the existing technical gates while separating the tests that prove
  them;
- name the documentation products and reader tasks required at each milestone;
- contract a progressive example path from isolated Ray mechanics through manual
  integration, ordinary-user use, optimizer studies, and scaled operational
  workloads;
- require examples to use the evolving public implementation and tests to
  exercise the boundary they claim;
- update the Milestone 2 plan so implementation, tests, documentation, example,
  review, and handoff develop together.

## Current artifact review status

| Artifact | Status | Review note |
| --- | --- | --- |
| Product roadmap | Governing; accepted | Not reopened by the milestone-gate rebuild. |
| Project decisions | Accepted with merged package | Contains cross-milestone technical choices only. |
| Framework-native review | Accepted with merged package | Standing review remains separate from milestone gates. |
| Milestone 1 gates | Pending revised review | Must establish the complete project-level closure contract. |
| Milestone 2–6 gates | Pending revised review | Must gate tests, documentation, examples, evidence, and handoff as well as capability. |
| Research report | Accepted as explanatory basis | Does not own completion or deferral policy. |
| Evidence ledger | Accepted as Milestone 1 audit record | Named milestone qualification obligations remain authoritative only through their gate files. |
| Evolutionary-controller plan | Pending revised review | Must sequence all Milestone 2 project products, not only controller implementation. |

## Closure

Milestone 1 remains open until the revised project-complete milestone gates and
Milestone 2 plan are reviewed and every Milestone 1 gate is accepted, corrected,
or retained as an explicit blocker.
