# Milestone 2 gates — evolutionary subsystem

Status: active milestone gate  
Date: 2026-07-24

## Governing basis

The roadmap and accepted project decisions govern this milestone. Milestone 1 is
closed. The controller must preserve the accepted single-parent population
policy while leaving Ray, Lightning, and PyTorch lifecycle execution to the
integration milestone.

## Milestone result

ClanBasedTuning has an independently invokable, tested, documented, and
inspectable evolutionary controller that expresses the population-decision side
of Clan Tuning with the narrowest coherent responsibility.

The controller is designed for its immediate Ray Tune consumer without making
Ray integration part of the controller product. Choosing and implementing the
Ray invocation seam belongs to Milestone 3.

## Capability and responsibility gates

### M2.1 The controller owns one complete population decision

Given one complete population result, the controller:

- compares member-local fitness under one explicit metric direction;
- selects the sole winning member;
- derives one legal optimizer configuration for every next-generation member;
- records the member-to-parent relationship and policy information needed to
  explain the transition; and
- returns one complete decision for framework-owned execution.

It does not collect live trial reports, choose when a round boundary occurs,
transfer model or optimizer state, construct optimizers, run training, schedule
resources, pause or resume trials, or manage checkpoints.

### M2.2 The public population and decision contracts are complete

The controller consumes one complete population result containing:

- stable member identity;
- comparable fitness;
- current optimizer configuration; and
- only the additional policy state the accepted controller design requires.

It produces one inspectable decision containing:

- the sole winning member whose model parameters, optimizer state, and optimizer
  configuration become the basis of the next generation;
- one legal optimizer configuration for every next-generation member;
- an explicit parent identity for every resulting member; and
- the policy information needed to explain and reproduce the transition.

The public model uses ordinary immutable or serialization-friendly values where
those values express the contract clearly. Ray `Trial`, `TuneController`,
checkpoint, actor, scheduler, and callback objects do not belong in it.

### M2.3 Selection and optimizer-configuration generation are deterministic and valid

- Metric direction and tie behavior are explicit.
- Missing, duplicate, NaN, infinite, or incomplete population input fails
  clearly.
- Exactly one parent and one complete next-generation configuration set are
  produced.
- Repeated execution from the same controller state and input produces the same
  decision.
- Model, data, batch, augmentation, and other gradient-defining mutation choices
  are outside the accepted controller surface.

The exact mutation and retention policy is documented and tested. The gate does
not prescribe an elite unless the accepted controller design chooses and
justifies one.

### M2.4 Controller state is limited to policy needs

The controller retains only state required to reproduce its accepted policy.
That state is explicit, inspectable, and serializable when persistence is
necessary. The controller does not mirror trial runtime, checkpoint contents,
resource state, experiment persistence, or framework progress clocks.

### M2.5 Incomplete populations do not produce valid transitions

The controller refuses to manufacture a partial evolutionary decision from a
missing or invalid population. Validation completes before any decision or
policy-state transition is emitted.

Process termination, checkpoint assignment, training restoration, and
operational recovery are not controller subsystems.

## Test gates

### M2.6 Focused tests prove the public policy contract

The controller suite covers ranking modes, ties, invalid fitness, duplicate and
incomplete populations, sole-parent selection, complete optimizer-configuration
output, optimizer-only boundaries, determinism, intentional state persistence,
no partial state transition after failure, and inspectable decision records.

### M2.7 The public contract is ready for native integration

Focused contract tests and design review establish that:

- member identities, fitness values, optimizer configurations, policy state, and
  decisions can be supplied without framework objects;
- one complete population input produces one complete decision through one
  explicit invocation;
- the decision exposes the parent and complete next-generation configurations
  needed by a later execution layer;
- no callback, report accumulator, trial registry, checkpoint abstraction, or
  scheduler lifecycle is hidden inside the controller; and
- the public structures can be translated directly from ordinary Ray trial
  identities, result values, and configuration mappings without introducing a
  second experiment schema.

This gate constrains the handoff; it does not choose or test the Ray scheduler or
adapter seam. That work begins in Milestone 3.

### M2.8 The controller remains independently invokable

The public controller contract can be exercised directly from explicit
population results and optimizer configurations without Ray installed or a
training job running.

## Documentation gates

### M2.9 Controller documentation transfers the complete policy model

The milestone delivers:

- the accepted controller design and responsibility boundary;
- public API and configuration reference;
- selection, tie, mutation, retention, state, and failure semantics;
- the decision-record model and reproducibility behavior;
- the integration obligations a later Ray path must satisfy; and
- a clear boundary between population decision and framework-owned execution.

A reader must not infer controller behavior from Ray internals or a later
integration example.

## Example gate

### M2.10 A public example makes the evolutionary transition inspectable

A small reproducible example invokes the public controller with explicit
population results and optimizer configurations. It makes the input population,
selected winner, resulting configurations, and explanation record visible and
explains how to read them.

Synthetic population results are appropriate because this milestone demonstrates
the decision subsystem. The complete training and checkpoint-driven transition
example begins in Milestone 3.

## Evidence, review, and handoff gates

### M2.11 The controller products agree

Implementation, focused tests, design and API documentation, decision records,
and example describe one public controller contract. Human review applies the
standing framework-native review to the controller boundary and records any
reopened assumption.

### M2.12 Milestone 3 receives a complete integration handoff

The handoff states:

- the population-result fields and completeness conditions the controller
  consumes;
- the transition decision it produces;
- intentional controller state and persistence requirements;
- the expected one-boundary, one-invocation semantics;
- the ordinary Ray concepts that map naturally to the public input and output;
- the framework responsibilities that remain outside the controller; and
- the questions Milestone 3 must answer when choosing and implementing the Ray
  invocation seam.

The handoff does not preselect a scheduler subclass, adapter, or private Ray
hook.

## Closure evidence

Milestone 2 closes with links to the accepted controller design, controller API,
focused policy and contract test results, public example and output,
decision-record reference, integration-readiness handoff, and human review.
