# Milestone 2 gates — evolutionary subsystem

Status: active completion gate under human review  
Date: 2026-07-25

## Governing basis

The roadmap and accepted project decisions govern this milestone. This gate
requires the independently invokable Clan population policy. Selection and
qualification of the Ray Tune invocation path belong to Milestone 3.

## Milestone result

ClanBasedTuning has a framework-independent, tested, documented, and inspectable
evolutionary controller that expresses the population-decision side of Clan
Tuning. It accepts ordinary data describing one complete population, selects the
sole parent, and produces the next optimizer-hyperparameter configurations.

The result is independently useful and ready for later framework integration. It
does not import Ray trial objects, subclass a Tune scheduler, communicate between
workers, transfer checkpoints, construct optimizers, apply live optimizer values,
or own training lifecycle.

## Capability and responsibility gates

### M2.1 The controller boundary is framework-independent

The accepted design gives the controller one coherent job: transform a complete
population result into the sole parent and next optimizer-hyperparameter
configurations.

Framework extraction and execution remain outside this component. The controller
may be tested with the plain data shape a future integration can construct, but
it does not depend on Ray, Lightning, or distributed runtime objects.

### M2.2 The population input and transition output are complete

The controller consumes one complete population result containing member
identity, comparable fitness, current optimizer-hyperparameter configuration,
and only the policy state the accepted design genuinely requires.

It produces enough information for an external lifecycle owner to identify the
sole winning member and obtain one legal next configuration for every member.
The accepted design documents the concrete data structure and associations; the
gate does not prescribe a record hierarchy or class layout.

The controller does not claim ownership of model parameters, optimizer state,
checkpoint contents, optimizer construction, training, or trials merely because
the selected member's external state will later be inherited.

### M2.3 Selection and configuration generation are deterministic and valid

- Metric direction and tie behavior are explicit.
- Missing, duplicate, non-finite, malformed, or incomplete population input fails
  clearly.
- Exactly one parent and one complete next-configuration set are produced.
- Repeated execution from the same accepted state and input produces the same
  decision.
- Variation is limited to optimizer hyperparameters; model, data, batch,
  augmentation, and other gradient-defining choices are rejected.

The exact mutation geometry, retention policy, boundary behavior, and randomness
model are documented and tested. The gate does not prescribe an elite, hidden
state, explicit seed, or persistence format before the accepted design justifies
one.

### M2.4 Controller state is limited to policy needs

The controller retains only state required by the accepted population policy.
It does not mirror framework population membership, trial runtime, checkpoint
contents, resources, experiment persistence, or optimizer construction.

If the accepted design is stateless, no serialization surface is added merely to
match a generic controller pattern. If state is required, its lifecycle,
authority, and deterministic restoration are documented and tested.

### M2.5 Invalid populations do not produce valid transitions

The controller refuses to manufacture a partial evolutionary decision from a
missing or invalid population. Validation and failure handling do not mutate
accepted policy state or emit partial output.

Operational process termination, collective failure handling, and checkpoint
recovery remain outside this controller milestone.

## Test gates

### M2.6 Focused tests prove the controller contract

Tests state their relevant preconditions and postconditions and cover:

- initialization behavior required by the accepted design;
- ranking direction and ties;
- invalid fitness and malformed or incomplete populations;
- sole-parent selection and complete next-configuration output;
- linear and logarithmic mutation geometry where supported;
- bounds and other declared legality rules;
- determinism and intentional state, if any;
- failure without partial advancement; and
- input/output immutability or ownership guarantees.

Tests avoid duplicated hard-coded export inventories when the package can inspect
its actual `__all__` or public attributes directly.

### M2.7 Plain-data seam tests preserve later integratability

Tests exercise the same ordinary data representation that a later Ray integration
can build after extracting framework-owned state. They prove that separate
controller instances agree when given the same logical population and policy
state.

These are compatibility tests, not Ray integration tests. They do not import Ray,
construct `Trial` objects, choose a scheduler hook, or claim checkpoint and
lifecycle execution.

### M2.8 The controller remains independently invokable

The accepted controller can be exercised directly from explicit population
results and optimizer-hyperparameter configurations. A later adapter does not
become the only route to policy testing, explanation, or reuse.

## Documentation gate

### M2.9 Engineering documentation transfers the controller model

Documentation is written for engineers integrating or maintaining the controller
and includes:

- the controller's purpose and explicit non-ownership boundaries;
- its lifecycle position before and after external training;
- the accepted input and output data structures and associations;
- selection, tie, mutation, bounds, randomness, state, and failure algorithms;
- constructor and method parameters with preconditions and postconditions;
- internal objects or modules where their contracts are nontrivial; and
- the exact responsibilities left to the future integration layer.

Lifecycle and ownership appear before detailed API syntax so a reader does not
mistake the controller for a Lightning callback, Ray scheduler, optimizer factory,
or population runtime.

## Example gate

### M2.10 A pet loop demonstrates repeated evolution

A small reproducible example runs several synthetic generations. An external pet
loop produces or samples member fitness, passes the complete population to the
controller, receives the selected parent and next configurations, and visibly
continues to the next generation.

The example exposes how configurations and winners evolve and explains where a
real training system would supply fitness and apply the returned decision. It
does not mock a Ray integration or reduce the demonstration to one isolated
method call.

## Evidence, review, and handoff gates

### M2.11 The controller products agree

The accepted design, implementation, focused tests, engineering documentation,
and pet-loop example describe one controller contract. No artifact claims a
public construction or framework integration API that the milestone has not
accepted.

Human review applies the standing framework-native and senior-engineering reviews
to the component itself.

### M2.12 Milestone 3 receives a complete integration handoff

The handoff states:

- the population fields and completeness conditions the controller consumes;
- the transition result it produces;
- intentional controller state and persistence requirements, if any;
- determinism and failure guarantees;
- the external model, optimizer, checkpoint, and lifecycle responsibilities; and
- the plain-data boundary where Milestone 3 will choose and qualify a Ray
  invocation path.

The handoff does not choose that Ray path in advance.

## Closure evidence

Milestone 2 closes with links to the accepted controller design, implementation,
focused and plain-data seam test results, engineering reference, pet-loop example,
human review, and Milestone 3 handoff.
