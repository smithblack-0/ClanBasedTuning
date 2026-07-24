# Milestone 2 gates — evolutionary subsystem

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

ClanBasedTuning has an independently invokable, documented, tested, and
inspectable evolutionary controller that expresses the population-decision side
of Clan Tuning through the narrowest viable Ray PBT responsibility.

## Capability and design gates

### M2.1 The Ray extension seam is qualified

- A version-pinned native Tune contract test exercises synchronous PBT with at
  least three trials through two population decisions.
- The seam preserves population synchronization, source-checkpoint preparation,
  checkpoint/configuration assignment, pause/resume ordering, and scheduler
  persistence.
- The Clan specialization does not reproduce substantial Tune controller
  behavior.
- If the seam fails this gate, the PBT-specialization decision is explicitly
  reopened before a direct controller is designed.

### M2.2 The population decision is deterministic and complete

- The controller consumes one complete population boundary.
- Metric direction and stable tie behavior are explicit.
- Missing, NaN, infinite, duplicate-member, or incomplete population input fails
  clearly.
- Exactly one parent is selected.

### M2.3 The next generation has the correct policy

- The selected parent state is the sole basis of the next generation.
- Ray transfers the parent checkpoint to every target member; the parent may
  retain its already-authoritative state rather than redundantly restoring
  itself.
- Exactly one elite optimizer configuration remains unmutated.
- Every other live member receives a legal target configuration.
- No member continues from an independent model or optimizer checkpoint.

### M2.4 Mutation is optimizer-only

- The accepted mutation surface identifies optimizer values without becoming a
  second experiment-configuration language.
- Model, data, batch, augmentation, and other gradient-defining mutations are
  rejected during setup.
- Native Ray mutation behavior is used where it fits; custom mutation logic has
  a demonstrated Clan-specific gap.

### M2.5 Planned completion and failure remain collective

- Planned completion is decided only at a complete population boundary and ends
  the complete population.
- Ordinary per-trial stopping is rejected for the supported controller path.
- A missing or failed member prevents exploitation; the controller does not
  continue with a smaller population.
- The controller identifies or invokes the narrowest Ray-native
  experiment-level outcome rather than implementing distributed process
  termination itself.

### M2.6 Native Ray experiment restoration is qualified

- `Tuner.restore` or the selected native equivalent restores controller and
  scheduler state, trial configuration, and latest trial checkpoints without a
  Clan-specific experiment manifest.
- Restored execution either resumes one coherent population state or fails
  explicitly; it may not silently combine incompatible member generations.

## Test gates

### M2.7 Focused policy tests prove the controller contract

The public controller test suite covers:

- minimizing and maximizing metrics;
- stable ties and deterministic repeatability;
- missing, NaN, infinite, duplicate-member, and incomplete-population input;
- sole-parent and complete target-set selection;
- elite preservation and legal optimizer-only mutation;
- rejection of nonoptimizer mutation declarations;
- collective completion and invalid-population behavior;
- serialization of only the policy state the Ray seam requires.

Tests may isolate policy functions where useful, but the public controller path
must also exercise their composition.

### M2.8 Version-pinned Ray contract tests prove lifecycle and restoration

Tests using native Tune trainables, reports, and checkpoints cover:

- at least three live trials and two consecutive population decisions;
- source checkpoint preparation before exploitation;
- checkpoint and configuration assignment to every target;
- pause and resume ordering;
- scheduler persistence;
- interruption after a completed population decision;
- interruption while a synchronous boundary is partially assembled;
- explicit failure rather than mixed-generation continuation when restoration
  cannot produce one coherent population.

Mocked direct scheduler calls alone cannot satisfy these lifecycle claims.

### M2.9 Failure ordering is tested, not inferred

- Missing results, trial errors, population loss, and unsupported per-trial
  stopping are exercised through the native scheduler path.
- Tests confirm that no target restarts before the authoritative source
  checkpoint and configuration are available.
- The test suite verifies that the controller remains independently usable
  without importing Lightning or constructing DDP.

## Documentation gates

### M2.10 Controller documentation enables independent use and review

The milestone delivers:

- a controller design and ownership document explaining why the subsystem exists,
  what Ray owns, what ClanBasedTuning changes, and what it explicitly does not
  own;
- public API and configuration reference for metric direction, mutation surface,
  tie behavior, elite policy, restoration assumptions, and collective completion;
- failure and limitation documentation, including the pinned Ray seam and the
  evidence that would reopen the design decision;
- a transition-record reference explaining parent, targets, elite, mutation,
  checkpoint lineage, and collective outcome;
- a Milestone 3 handoff describing the exact public controller contract and
  native Ray outputs the integration may rely on.

A reader must not need to infer policy or lifecycle behavior from Ray internals.

## Example and scientific-work gates

### M2.11 A native Ray example proves the subsystem

A small reproducible example:

- uses the actual public controller with real Tune trainables, reports, and
  checkpoints;
- runs at least three members through at least two generations;
- makes fitness, selected parent, elite, targets, mutations, checkpoint lineage,
  and collective completion visible;
- explains how to read the transition records and expected output;
- uses synthetic work only to isolate the evolutionary subsystem, not mocked
  scheduler calls or private shortcuts.

The example establishes mechanics. It does not claim Lightning integration or
scientific effectiveness.

## Evidence, review, and handoff gates

### M2.12 The milestone products agree

- The implementation, focused tests, Ray contract tests, documentation, and
  example describe one controller contract.
- Every version-sensitive assumption is linked to a contract test.
- Public examples and documentation import the same public controller accepted
  by tests.
- Human review applies the standing framework-native review and records any
  decision reopened by evidence.

### M2.13 Milestone 3 receives a complete integration contract

The handoff states:

- the report fields and complete-population condition the controller consumes;
- the source checkpoint, target configuration, restoration behavior, transition
  records, and collective outcome it produces;
- which lifecycle behavior remains owned by Ray;
- which Lightning, DDP, data, checkpoint-production, and resource responsibilities
  remain entirely with Milestone 3.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| Lightning validation/report production | Milestone 3 | This milestone consumes population reports; it does not produce them. | Generate exactly one comparable member-local report per qualifying Lightning boundary. | Multi-rank end-to-end integration tests, integration guide, and public example. |
| Real model/optimizer/data restoration | Milestone 3 | Milestone 2 uses framework-neutral synthetic trainables and checkpoints. | Restore Lightning model, optimizer, and data position through native Ray assignment. | Interrupted and normal multi-round integration tests. |
| Automated DDP, data, and resource assembly | Milestone 4 | Manual composition is sufficient for Milestone 3. | Provide the short user construction path. | User-path integration tests, quickstart example, and user guide. |
| General optimizer layouts | Milestone 5 | Controller mutation policy need not solve application to every optimizer structure. | Implement deterministic optimizer configuration resolution. | Multi-optimizer and parameter-group tests, reference docs, and examples. |
| Production storage and cluster-failure qualification | Milestone 6 | Functional Ray restoration is required now; production operating envelopes are not. | Qualify persistent storage, cluster interruption, diagnosis, and restoration at industry scope. | Industry readiness audit, failure tests, runbooks, and recovery examples. |

## Closure evidence

Milestone 2 closes with links to the accepted controller design, public API
reference, focused test suite, version-pinned Ray contract suite, native Ray
example and output, transition records, review result, and Milestone 3 handoff.
