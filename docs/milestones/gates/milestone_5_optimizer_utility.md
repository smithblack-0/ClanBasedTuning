# Milestone 5 gates — optimizer utility

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

ClanBasedTuning applies evolved optimizer configurations predictably across
realistic optimizer, parameter-group, and multi-optimizer layouts.

## Gates

### M5.1 Configuration application has one explicit owner

- The `OptimizerAdapter` system, or an accepted replacement, is the sole owner of
  mapping evolved configuration values onto constructed optimizers.
- It does not construct optimizers, reinterpret the complete Tune configuration,
  or compete with Lightning's optimizer lifecycle.

### M5.2 Default behavior is direct and predictable

- By default, a declared value maps to the same-named optimizer hyperparameter.
- Missing, unsupported, or inapplicable declarations fail clearly.
- Declared values are never silently ignored.

### M5.3 Specific targeting has deterministic precedence

- Rules may target documented combinations of optimizer type, optimizer
  instance/reference, parameter group, and explicit remapping.
- When several rules match, one documented specificity order determines the
  result.
- Ambiguity at equal precedence fails rather than depending on iteration order.

### M5.4 Multiple optimizers and parameter groups are covered

- The system applies values to intended optimizers and groups without leaking to
  unrelated ones.
- Momentum, moments, scheduler interaction, and restored state remain coherent
  with the checkpoint authority established by earlier milestones.

### M5.5 The utility remains concise and inspectable

- Ordinary dictionaries or direct functions are preferred where they express the
  contract without a new subsystem.
- Every abstraction eliminates real repeated logic or establishes a necessary
  public contract.
- Resolution can be explained and audited without reading framework internals.

### M5.6 Tests, reference documentation, and examples agree

Unit and integration tests cover default mapping, remapping, specificity,
ambiguity, failure behavior, multiple optimizers, specialized parameter groups,
and checkpoint restoration. Reference documentation and examples show the same
resolution model.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| Production-scale optimizer diagnostics and support qualification | Milestone 6 | Milestone 5 establishes correct utility behavior in the declared integration envelope. | Expose useful diagnostics and qualify optimizer behavior under serious distributed workloads. | Industry readiness audit and scaled tests. |
