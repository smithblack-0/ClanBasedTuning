# Milestone 2 gates — evolutionary subsystem

Status: active milestone gate  
Date: 2026-07-24

## Governing basis

The roadmap and accepted project decisions govern this milestone. Milestone 1 is
closed. Milestone 2 delivers the independently invokable population policy;
Milestone 3 chooses and implements the Ray-backed execution seam and complete
training workflow.

## Milestone result

ClanBasedTuning has an independently invokable, tested, documented, and
inspectable evolutionary controller that expresses the population-decision side
of Clan Tuning with the narrowest coherent responsibility.

The controller is reasonably compatible with its expected consumer without
absorbing that consumer's framework lifecycle or preselecting its integration
form.

## Capability and responsibility gates

### M2.1 The controller expresses the Clan population policy

Given the information required to judge one population boundary, the controller:

- compares the members' fitness under an explicit policy;
- selects the sole winning member whose training state is the basis of the next
  generation; and
- emits the optimizer-configuration values required for the next generation.

The gate does not prescribe a class hierarchy, fixed membership model, record
schema, tie algorithm, elite layout, perturbation mechanism, or state
representation. The accepted design must justify those choices within this
behavioral envelope.

### M2.2 The controller owns policy, not execution

The controller may own only the information and state needed to make its
population decision. It does not:

- collect live framework reports or choose when training reaches a boundary;
- transfer or apply model or optimizer state;
- mutate a live optimizer;
- construct optimizers or run training;
- schedule resources, trials, actors, or distributed workers; or
- own checkpoints, pause/resume, restoration, or operational recovery.

It emits configuration values and a policy result for later execution by the
appropriate owners.

### M2.3 The variation surface remains optimizer-side

The controller may vary only optimizer-side choices that operate after the
shared gradient has been produced. Model, data, batch, augmentation, and other
choices that alter the shared-gradient workload are outside this milestone's
accepted policy surface.

The exact supported optimizer-configuration domain is an accepted design and
documentation question. Unsupported inputs must not be silently treated as valid
policy output.

### M2.4 The public contract is independent and reasonably compatible

The public controller can be invoked directly without Ray, Lightning, PyTorch
distributed execution, or a running training job. Its input and output expose the
policy information an ordinary consumer needs without requiring live framework
objects or a second experiment framework.

Reasonable compatibility is demonstrated through tests and examples. This gate
does not prescribe the later adapter, scheduler hook, callback path, checkpoint
mapping, or framework seam.

### M2.5 Invalid populations cannot become valid transitions

Incomplete, contradictory, or otherwise invalid population information cannot
produce a valid next-generation decision. The accepted design states its
validity conditions, randomness or state contract, and failure behavior clearly
enough that callers and tests can distinguish a valid transition from refusal.

The gate requires reproducible and auditable behavior under the documented
policy contract. It does not require one particular deterministic tie rule,
serialization format, transaction object, or state machine.

## Test gates

### M2.6 Focused tests prove the policy contract

The focused suite exercises:

- sole-parent selection under the supported fitness policy;
- complete next-generation optimizer-configuration output;
- the optimizer-only variation boundary;
- invalid and incomplete population behavior;
- the accepted design's randomness, state, and repeatability claims; and
- failure behavior that prevents an invalid result from being presented as a
  valid transition.

Tests target the chosen public contract without importing Milestone 3's Ray,
Lightning, checkpoint, or distributed lifecycle.

### M2.7 Compatibility is exercised without implementing integration

Tests demonstrate that a representative ordinary caller can supply the policy
input and consume the result without framework-owned runtime objects. They may
use Ray-shaped values or other realistic consumer data where useful, but they do
not select, implement, or qualify the Ray invocation seam.

## Documentation gates

### M2.8 Controller documentation transfers the accepted policy model

The milestone documents:

- the controller's purpose and responsibility boundary;
- its public input, output, and supported configuration surface;
- selection and next-generation policy behavior;
- any intentional state or randomness;
- validity, failure, and limitation semantics; and
- what remains for framework-owned execution in Milestone 3.

Documentation explains the accepted design without presenting its choices as the
only gate-compliant architecture.

## Example gate

### M2.9 A public example makes the evolutionary decision inspectable

A small reproducible example invokes the public controller directly, shows the
population information supplied, the selected winner, and the emitted
next-generation optimizer configurations, and explains how to interpret the
result.

Synthetic population results are appropriate because this milestone demonstrates
the policy itself. A complete checkpoint-driven training transition belongs to
Milestone 3.

## Review and downstream gate

### M2.10 The delivered products agree

Implementation, focused tests, design and API documentation, and the public
example describe one controller contract and policy. Human review applies the
standing framework-native and gate-boundary reviews and rejects design leakage
into the gate.

### M2.11 Milestone 3 can rely on the public policy capability

Milestone 3 receives a stable, independently exercised public controller and its
documented behavior. The handoff is the public capability and evidence, not a
predesigned Ray adapter or cross-milestone execution plan.

Any integration dependency established during Milestone 2 that is not already
covered by the Milestone 3 gate is inserted directly into that gate at the
behavioral level: what current capability must be connected or preserved, and
what observable result must occur. The inserted requirement may not choose the
future class, hook, adapter, framework seam, or strategy. Speculative mechanisms
remain non-authoritative scratchwork until Milestone 3 design work evaluates
them.

## Closure evidence

Milestone 2 closes with the accepted controller design and implementation,
focused policy and compatibility tests, public documentation, an independently
runnable example and output, human review, and evidence that the public
capability is sufficient for Milestone 3 without prescribing its implementation.
