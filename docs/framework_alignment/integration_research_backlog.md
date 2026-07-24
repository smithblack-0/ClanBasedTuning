# Integration research backlog

Status: advisory input for later milestones  
Date: 2026-07-24

## Purpose

This backlog preserves framework-specific questions discovered during
Milestone 1 research that do not belong in the standing review or the
evolutionary-controller plan.

Items here are not accepted implementation designs. Each later milestone should
select the questions it depends on, investigate the live framework version, and
move accepted results into its own design, tests, support reference, and user
documentation.

## Round cadence and continuation

### Current direction

Lightning owns validation cadence. Qualified batch-based or fractional
subepoch validation should define the practical Clan round boundary.

### Questions to resolve

- Which `val_check_interval` and `check_val_every_n_epoch` combinations cause
  every member to enter validation at the same loop position?
- Which loaders allow Lightning to checkpoint and resume the exact training
  position after Ray pauses or recreates the trial?
- How do iterable datasets, reloadable loaders, gradient accumulation, and
  multiple validation loaders affect that claim?
- Which callback event emits exactly one fitness report and one checkpoint for a
  qualifying validation without reporting sanity checks or unrelated metrics?

### Evidence required

A multi-member test that pauses at a subepoch validation boundary, recreates the
trials from their assigned checkpoints, and demonstrates the expected next
training data and optimizer step.

## Member-local checkpointing and restore

### Current direction

Use Ray's standard Lightning report/checkpoint integration. Narrowly specialize
Lightning only where ordinary DDP rank-zero checkpoint assumptions prevent each
divergent trial from producing its own checkpoint.

### Questions to resolve

- What is the smallest supported Strategy override that permits every Tune trial
  to save through the standard callback?
- Does the callback and FunctionTrainable path retain the checkpoint long enough
  for synchronous PBT source assignment under local and remote storage?
- Which restore hook can reconcile evolved optimizer values after inherited
  optimizer state without taking ownership of optimizer construction?
- How are multiple optimizers and parameter groups exposed to the later
  `OptimizerAdapter` without creating a temporary competing schema?

### Evidence required

Select a nonzero DDP rank as the parent, restore both source and target trials
through native Ray and Lightning behavior, verify inherited model and optimizer
state, and verify target configuration reconciliation afterward.

## DDP construction and state synchronization

### Current direction

Use native PyTorch DDP for initial synchronization, gradient reduction, and
wrapper behavior. Prevent runtime state synchronization that erases intended
member divergence.

### Questions to resolve

- At what Lightning hook can the wrapped DDP module be configured without
  reimplementing setup?
- Can native `init_sync` remain enabled while later buffer broadcast is disabled
  before the first training forward?
- Which registered buffers should remain local, and which model families require
  explicit unsupported-status handling?
- Which topology checks are already native, and which Clan-specific compatibility
  checks remain necessary?

### Evidence required

A version-pinned Lightning contract test demonstrating initial equality, common
reduced gradients, member divergence, preserved local buffers, and no duplicate
collective implementation.

## Population admission and rendezvous

### Current direction

One Ray trial is one member, and the whole population must be resident before
DDP begins. The primary preflight belongs at the future assembly boundary, not
inside the scheduler alone.

### Questions to resolve

- Which public Ray objects expose generated trial count, concurrency, per-trial
  resource requests, and available dedicated allocation before `Tuner.fit()`?
- How should the supported path reject grid expansion, alternate search
  algorithms, actor reuse, or competing workloads without inventing a new Ray
  configuration language?
- How are rank, world size, rendezvous endpoint, and trial identity supplied to
  Lightning while keeping Ray as the trial owner?
- Which parts can remain manual in the integratable-orchestration milestone and
  which belong only to the later usability frontend?

### Evidence required

A preflight test that rejects incomplete residency before any process enters the
collective, followed by a complete-population launch and repeated rendezvous
after exploitation.

## Fitness data and reporting

### Current direction

Training loaders remain normally sharded. Fitness evaluation uses one
deterministic held-out workload for every member, and the fitness scalar remains
local to the Tune trial.

### Questions to resolve

- Can a standard PyTorch sampler configuration cover the supported map-style
  datasets without a custom sampler class?
- How are validation transforms, random state, drop behavior, and loader length
  kept equivalent?
- What user-facing metric contract prevents accidental `sync_dist=True` or
  selection from a partially reduced metric?
- How does the reporting callback distinguish the final comparable metric from
  step metrics and sanity checks?

### Evidence required

An end-to-end test in which members deliberately produce different fitness on
identical evaluation examples and Ray ranks them without DDP metric reduction.

## Optimizer and precision behavior

### Current direction

Milestone 3 integration may initially support ordinary automatic optimization
and a narrow optimizer layout. General mappings belong to the later
optimizer-utility milestone.

### Questions to resolve

- Which optimizer values can be reconciled safely after state restoration?
- How should active Lightning LR schedulers be detected and rejected until a
  combined authority exists?
- Does BF16 preserve the expected common-gradient and divergent-update behavior?
- Can FP16 dynamic loss scaling remain coherent when member parameters and local
  overflow behavior diverge?
- How do gradient accumulation and skipped optimizer steps affect round
  synchronization?

### Evidence required

Direct divergent-member tests for each claimed precision and optimization mode.
Ordinary DDP support is not sufficient evidence.

## Failure, stopping, and recovery

### Current direction

A member error fails or stops the complete Clan. Planned completion occurs at a
synchronized population boundary. Whole-experiment recovery across an
interrupted boundary is deferred.

### Questions to resolve

- Which Ray scheduler or experiment seam can request collective planned
  completion without per-trial stop ordering?
- How does one trial error propagate to every actor and avoid indefinite DDP
  waits?
- Which timeouts and diagnostics identify the failed member and current round?
- What generation authority and persistence transaction would later make
  interrupted-round experiment restore coherent?

### Evidence required

Initial integration must prove collective failure and clean collective planned
completion. Recovery design is not required until the industry milestone claims
it.

## Backlog maintenance

When a later milestone resolves an item:

1. record the source review and probe in the evidence ledger or the milestone's
   own evidence record;
2. move the accepted contract into the owning design or support reference;
3. remove obsolete preliminary direction from this backlog;
4. update the standing review only if the result changes a durable project-wide
   gate.
