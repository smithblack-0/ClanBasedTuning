# Milestone 3 gates — integratable orchestration subsystems

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

The evolutionary controller and Clan-specific training primitives can be
manually composed into a documented, tested, inspectable, real distributed
Lightning workflow in which Clan Tuning completes multiple rounds end to end.

## Capability and design gates

### M3.1 Manual composition preserves framework ownership

- The workflow explicitly composes Ray trials, Lightning Trainer behavior,
  PyTorch DDP, model wrapping, data configuration, and Clan-specific primitives.
- ClanBasedTuning adds only the seams required by the accepted project decisions.
- Package-managed convenience is not required, but no second training loop,
  scheduler, checkpoint system, or collective implementation is introduced.

### M3.2 Population admission is coherent

- One Tune trial maps to one DDP member and one dedicated device or declared
  supported resource unit.
- The complete population is concurrently resident before any member enters the
  collective.
- Population count, concurrency, rank, world size, and rendezvous information
  agree or setup fails before distributed work begins.

### M3.3 Native DDP produces shared gradients and member divergence

- Members begin each round from the inherited common state.
- Native DDP produces common reduced gradients from independently partitioned
  training batches.
- Member-local optimizer state/configuration produces observable parameter
  divergence after the shared gradient.
- Runtime synchronization, including buffer behavior, does not erase intended
  divergence.

### M3.4 Lightning produces coherent round boundaries

- A documented Lightning validation cadence causes every member to enter the
  qualifying boundary at the same training-loop position.
- Sanity checks, unrelated validation, and intermediate logging do not trigger
  evolution.
- The supported loader and accumulation configurations resume at the documented
  next training position after pause or trial recreation.

### M3.5 Fitness is comparable and member-local

- Training data is partitioned normally.
- Every member evaluates the same held-out examples with equivalent transforms,
  ordering, and loader length.
- Each member reports one local fitness value; DDP metric reduction does not
  combine candidate scores before Ray comparison.

### M3.6 Every member can supply a native Lightning checkpoint

- Every divergent member can produce a trial-local Lightning checkpoint at the
  qualifying boundary, including a member whose DDP rank is not global rank
  zero.
- Ray's normal Lightning report/checkpoint path remains the transfer mechanism.
- The implementation uses the narrowest Lightning seam necessary to overcome
  ordinary replica-equivalence assumptions.

### M3.7 Winner state reload and optimizer reconciliation are correct

- Ray assigns the selected parent checkpoint to every target trial.
- Lightning restores model and optimizer state through its normal lifecycle.
- ClanBasedTuning then reapplies only the receiving member's evolved optimizer
  values.
- Momentum, moments, step counters, and other inherited optimizer history remain
  from the parent.
- Competing LR scheduler authority is either integrated explicitly or rejected
  by the supported configuration.

### M3.8 Functional interruption and restoration work end to end

- A completed-round interruption restores the current generation and continues
  through another full round.
- An interruption during a partially assembled synchronous boundary follows the
  Ray behavior qualified in Milestone 2 and restores compatible Lightning trial
  states or fails explicitly.
- No custom generation manifest is added unless direct evidence demonstrates a
  native gap and the design is approved.

### M3.9 Failure is collective and diagnosable

- Failure of one member terminates or invalidates the complete active Clan.
- No surviving member continues indefinitely in a broken collective.
- The error identifies the failed member and lifecycle boundary sufficiently for
  an engineer to diagnose the integration.

## Test gates

### M3.10 Focused tests cover every Clan-specific primitive

- Each integration primitive has direct tests for its input, output, lifecycle
  position, ownership boundary, and failure behavior.
- Tests cover resource and population preflight, rank/rendezvous mapping,
  qualifying report selection, comparable-fitness configuration, member-local
  checkpoint permission, optimizer reconciliation, and unsupported setup.
- Component tests do not claim end-to-end support that only the complete workflow
  can establish.

### M3.11 Version-pinned framework contract tests protect native seams

Tests pin and exercise the selected Lightning, Ray, and PyTorch behavior for:

- DDP initial synchronization, gradient reduction, and runtime buffer behavior;
- Lightning validation timing and exact report/checkpoint event selection;
- member-local checkpoint creation from a nonzero DDP rank;
- native Ray checkpoint assignment and Lightning restoration ordering;
- optimizer reconciliation after restore;
- supported accumulation, precision, and loader behavior.

A framework upgrade that changes one of these assumptions must fail a contract
test before it becomes a silent behavioral change.

### M3.12 End-to-end integration tests prove the public manual path

On every claimed topology, tests use the public manual composition to prove:

- at least three concurrently resident members complete at least two rounds;
- independent training batches produce one common reduced gradient;
- member-local optimizer policy creates divergence;
- identical held-out evaluation produces distinct local fitness values;
- one parent supplies every next-generation target checkpoint;
- inherited model and optimizer state plus target configuration continue training;
- completed-boundary and partial-boundary interruption follow the documented
  restoration contract;
- one-member failure invalidates the complete Clan without indefinite waits.

Any accelerator support claim requires a direct accelerator integration run;
CPU evidence alone cannot qualify it.

### M3.13 Negative integration tests protect the support boundary

The public path rejects or clearly fails on:

- insufficient concurrent resources or inconsistent population/world-size data;
- unsupported validation cadence or loader continuation;
- distributed fitness reduction that erases candidate differences;
- missing member-local checkpoints;
- incompatible optimizer or LR-scheduler authority;
- population loss, unsupported precision, or other configurations outside the
  declared envelope.

## Documentation gates

### M3.14 Engineering documentation enables manual integration and review

The milestone delivers:

- an integration design explaining component ownership, lifecycle, and data/state
  flow across Ray, Lightning, PyTorch, and ClanBasedTuning;
- a manual integration guide that enables a Lightning developer to compose the
  supported workflow through public components;
- reference documentation for every Clan-specific primitive and required
  framework setting;
- a support and limitation reference covering topology, versions, loader,
  precision, optimizer, stopping, restoration, and checkpoint assumptions;
- failure and diagnostic guidance explaining the round, member, and state visible
  in errors and transition records;
- an explanation of how to inspect a complete round and verify shared gradients,
  divergence, fitness, parent selection, and continuation.

A reader must not need to reconstruct the workflow from tests or source code.

## Example and scientific-work gates

### M3.15 A deterministic mechanics example exposes the complete workflow

A reproducible public manual-composition example:

- completes multiple rounds with real Lightning training, native DDP, comparable
  evaluation, Ray selection, checkpoint inheritance, and continued training;
- makes shared gradients, divergence, fitness, parent, target, and checkpoint
  lineage inspectable;
- uses no private construction shortcut unavailable to advanced users;
- explains expected output and how to diagnose a failed lifecycle boundary.

### M3.16 An initial scientific example exercises a meaningful workload

A second public-package example or experiment:

- uses a real training task capable of illustrating optimizer-policy adaptation,
  rather than synthetic fitness or mocked control flow;
- records the fixed workload, member configurations, round cadence, fitness,
  selected policy path, training cost, and limitations;
- reports interpretable results whether favorable, neutral, or unfavorable;
- is reproducible enough to become the foundation for richer Milestone 5 studies.

The scientific result need not establish the method's value. It must establish
that the public integration can investigate it honestly.

## Evidence, review, and handoff gates

### M3.17 The milestone products agree

- Implementation, focused tests, framework contract tests, end-to-end tests,
  documentation, and both examples describe one supported manual workflow.
- Every support claim is no broader than the tested topology and framework
  envelope.
- Human review applies the standing framework-native review to each custom seam
  and records remaining blockers or assigned deferrals.

### M3.18 Milestone 4 receives a precise usability handoff

The handoff identifies:

- the complete manual sequence an ordinary user should no longer perform;
- the proven lower-level primitives and public contracts the convenience layer
  must compose rather than replace;
- the supported settings and failures the simple path must preserve;
- the advanced manual example and documentation that must remain available.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| Short package-managed setup | Milestone 4 | This milestone proves composability through explicit manual assembly. | Remove user-facing DDP, wrapping, data, rendezvous, and plugin-construction ceremony without hiding framework ownership. | Complete simple-path test suite, quickstart example, user guide, and fresh-user walkthrough. |
| Broad optimizer and parameter-group mapping | Milestone 5 | A narrow documented optimizer layout is sufficient to prove end-to-end mechanics. | Support realistic optimizer layouts predictably. | Utility gate suite, reference docs, public examples, and optimizer-policy study. |
| Production observability, model sharding, and cluster recovery | Milestone 6 | Milestone 3 proves functional behavior in its declared test topology. | Qualify serious workloads, persistent storage, cluster failure, restoration, and diagnosis. | Industry readiness audit, direct hardware/failure tests, operations docs, and scaled examples. |

## Closure evidence

Milestone 3 closes with links to the integration design, primitive tests,
version-pinned framework contract tests, end-to-end and failure test results,
manual integration guide, support reference, mechanics example, scientific
example and results, human review, and Milestone 4 handoff.
