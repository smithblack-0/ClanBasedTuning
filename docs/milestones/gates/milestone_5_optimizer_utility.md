# Milestone 5 gates — optimizer utility

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

ClanBasedTuning applies evolved optimizer configurations predictably across
realistic optimizer, parameter-group, multi-optimizer, and restoration layouts.
The behavior is tested, documented, demonstrated through public examples, and
useful for interpretable optimizer-policy studies.

## Capability and design gates

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
- Momentum, moments, step counters, scheduler interaction, and restored state
  remain coherent with the checkpoint authority established by earlier
  milestones.
- Unsupported optimizer or scheduler authority fails before training continues.

### M5.5 The utility remains concise and inspectable

- Ordinary dictionaries or direct functions are preferred where they express the
  contract without a new subsystem.
- Every abstraction eliminates real repeated logic or establishes a necessary
  public contract.
- Resolution can be explained and audited without reading framework internals.

## Test gates

### M5.6 Resolution-unit tests cover the complete rule model

The focused suite covers:

- same-name default mapping;
- explicit remapping;
- optimizer type, optimizer reference, and parameter-group targeting;
- specificity ordering and equal-precedence ambiguity;
- missing, unsupported, duplicate, or inapplicable declarations;
- values whose type or range the selected optimizer cannot accept;
- deterministic resolution independent of dictionary or registration order;
- confirmation that unrelated optimizers and groups remain unchanged.

### M5.7 Integration tests cover realistic optimizer lifecycles

Using the public Clan workflow, tests cover:

- at least two realistic optimizer types;
- multiple parameter groups with different target values;
- multiple optimizers in one Lightning module where the supported optimization
  lifecycle permits them;
- checkpoint inheritance followed by target-configuration reconciliation;
- preservation of optimizer history such as momentum, moments, and step counts;
- documented interaction with Lightning LR schedulers or clear rejection where
  authority would conflict;
- ordinary and advanced construction paths from Milestone 4.

### M5.8 Failure and regression tests prevent silent configuration drift

- Every declared value is either applied to a uniquely identified target or
  causes a clear failure.
- Ambiguous or stale rules fail before an optimizer step.
- Serialization and restoration reproduce the same resolution behavior.
- Tests protect public precedence and failure semantics from accidental changes.

## Documentation gates

### M5.9 The optimizer-resolution model is fully documented

The milestone delivers:

- a conceptual guide explaining when configuration is resolved and why
  Lightning retains optimizer-construction authority;
- a complete reference for default mapping, remapping, targeting dimensions,
  specificity order, ambiguity, and failure behavior;
- worked tables showing which rule wins for representative realistic layouts;
- guidance for checkpoint restoration, inherited optimizer history, and
  LR-scheduler interaction;
- extension guidance for supporting an optimizer layout without bypassing the
  public resolution contract;
- an updated support reference and troubleshooting guide for ordinary users and
  advanced integrators.

A reader must be able to predict the destination of every declared value without
reading implementation code.

## Example and scientific-work gates

### M5.10 Public examples demonstrate realistic optimizer layouts

The milestone includes executable public-package examples for:

- multiple parameter groups with distinct evolved values;
- multiple optimizers or the broadest realistic multi-optimizer layout the
  supported Lightning lifecycle permits;
- explicit remapping and specificity;
- checkpoint inheritance followed by configuration reconciliation;
- at least one failure example that explains an ambiguous or unsupported rule.

Each example explains expected resolution and how to inspect applied values and
preserved optimizer state.

### M5.11 An optimizer-policy study uses the complete public system

At least one reproducible study:

- uses the Milestone 4 ordinary path unless advanced composition is genuinely
  required;
- tunes realistic optimizer-side values over multiple rounds;
- records candidate configurations, selected policy path, fitness, training
  behavior, computation cost, and final outcome;
- distinguishes the Clan method's behavior from workload and framework effects;
- reports favorable, neutral, or unfavorable findings honestly;
- produces artifacts suitable for comparison in later scaled studies.

The gate requires an interpretable experiment, not a favorable result.

## Evidence, review, and handoff gates

### M5.12 The milestone products agree

- Resolution code, focused tests, integration tests, references, troubleshooting,
  examples, and study all use one public rule model.
- Public examples are executable tests of the documented behavior rather than
  separate demonstration logic.
- Human review confirms that the utility has one owner and has not become a
  package-wide experiment schema or optimizer factory.

### M5.13 Milestone 6 receives a qualified utility envelope

The handoff identifies:

- optimizer types, parameter-group forms, scheduler interactions, precision
  modes, and restoration paths directly tested;
- emitted diagnostics required to explain resolution at production scale;
- performance or state-size costs observed in realistic workloads;
- unsupported layouts removed from the industry support envelope or assigned to
  explicit Milestone 6 qualification.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| Production-scale optimizer diagnostics and support qualification | Milestone 6 | Milestone 5 establishes correct utility behavior in the declared integration envelope. | Expose useful diagnostics and qualify optimizer behavior under serious distributed workloads. | Industry readiness audit, scaled integration and restoration tests, support matrix, operator docs, and public workloads. |

## Closure evidence

Milestone 5 closes with links to the accepted resolution design, focused and
integration test results, optimizer reference and guides, realistic layout
examples, optimizer-policy study and artifacts, human review, and Milestone 6
support handoff.
