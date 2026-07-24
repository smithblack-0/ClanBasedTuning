# Milestone 2 gates — evolutionary subsystem

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

ClanBasedTuning has an independently invokable evolutionary controller that
expresses the population-decision side of Clan Tuning through the narrowest
viable Ray PBT responsibility.

## Gates

### M2.1 The Ray extension seam is qualified

- A version-pinned native Tune test exercises synchronous PBT with at least three
  trials through two population decisions.
- The test establishes population synchronization, source checkpoint
  preparation, checkpoint/configuration assignment, pause/resume ordering, and
  scheduler persistence.
- The Clan specialization does not reproduce substantial Tune controller
  behavior.
- If the seam fails this gate, the PBT-specialization decision is explicitly
  reopened before a direct controller is designed.

### M2.2 The population decision is deterministic and complete

- The controller consumes one complete population boundary.
- Metric direction and stable tie behavior are documented and tested.
- Missing, NaN, infinite, duplicate-member, or incomplete population input fails
  clearly; equal fitness values use the documented tie rule.
- Exactly one parent is selected.

### M2.3 The next generation has the correct policy

- The selected parent state is the sole basis of the next generation.
- Ray transfers the parent checkpoint to every target member; the parent may
  retain its already-authoritative state rather than redundantly restoring itself.
- Exactly one elite optimizer configuration remains unmutated.
- Every other live member receives a legal target configuration.
- No member continues from an independent model or optimizer checkpoint.

### M2.4 Mutation is optimizer-only

- The accepted mutation surface can identify optimizer values without becoming a
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
- The controller identifies or invokes the narrowest Ray-native experiment-level
  outcome rather than implementing distributed process termination itself.

### M2.6 Native Ray experiment restoration is qualified

- `Tuner.restore` or the selected native equivalent restores the controller,
  scheduler state, trial configuration, and latest trial checkpoints without a
  Clan-specific experiment manifest.
- Tests cover interruption after a completed population decision and interruption
  while a synchronous population boundary is partially assembled.
- Restored execution either resumes one coherent population state or fails
  explicitly; it may not silently combine incompatible member generations.

### M2.7 The controller is independent and inspectable

- The public controller contract can be used and tested without Lightning or
  DDP.
- State retained by the controller is limited to what the Ray seam genuinely
  requires.
- Transition records make parent, targets, elite, mutation, and collective
  outcome inspectable.
- Documentation explains non-obvious policy, lifecycle, persistence, and failure
  decisions.

### M2.8 A native example proves the subsystem

A small Ray example using real trainables, reports, and checkpoints completes
multiple generations and visibly matches the controller contract. Mocked direct
scheduler calls are insufficient as the milestone example.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| Lightning validation/report production | Milestone 3 | This milestone consumes population reports; it does not produce them. | Generate exactly one comparable member-local report per qualifying Lightning boundary. | Multi-rank end-to-end integration test. |
| Real model/optimizer/data restoration | Milestone 3 | Milestone 2 uses framework-neutral synthetic trainables and checkpoints. | Restore Lightning model, optimizer, and data position through native Ray assignment. | Interrupted and normal multi-round integration tests. |
| Automated DDP, data, and resource assembly | Milestone 4 | Manual composition is sufficient for Milestone 3. | Provide the short user construction path. | User-path integration test and guide. |
| General optimizer layouts | Milestone 5 | Controller mutation policy need not solve application to every optimizer structure. | Implement deterministic optimizer configuration resolution. | Multi-optimizer and parameter-group tests. |
| Production storage and cluster-failure qualification | Milestone 6 | Functional Ray restoration is required now; production operating envelopes are not. | Qualify persistent storage, cluster interruption, diagnosis, and restoration at industry scope. | Industry readiness audit and failure tests. |
