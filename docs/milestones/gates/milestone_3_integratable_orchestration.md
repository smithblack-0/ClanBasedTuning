# Milestone 3 gates — integratable orchestration subsystems

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

The evolutionary controller and Clan-specific training primitives can be
manually composed into a real distributed Lightning workflow in which Clan
Tuning completes multiple rounds end to end.

## Gates

### M3.1 Manual composition preserves framework ownership

- The example explicitly composes Ray trials, Lightning Trainer behavior,
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

### M3.10 The example is technically and scientifically meaningful

The public manual composition completes multiple rounds, shows shared gradients,
member divergence, comparable fitness, sole-parent selection, checkpoint
inheritance, and continued training on a workload capable of illustrating the
method rather than only mocked control flow.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| Short package-managed setup | Milestone 4 | This milestone proves composability through explicit manual assembly. | Remove user-facing DDP, wrapping, data, and plugin construction ceremony. | Complete simple-path integration test and user guide. |
| Broad optimizer and parameter-group mapping | Milestone 5 | A narrow documented optimizer layout is sufficient to prove end-to-end mechanics. | Support realistic optimizer layouts predictably. | Utility gate suite. |
| Production observability, model sharding, and cluster recovery | Milestone 6 | Milestone 3 proves functional behavior in its declared test topology. | Qualify serious workloads, persistent storage, cluster failure, restoration, and diagnosis. | Industry readiness audit on declared hardware/framework envelopes. |
