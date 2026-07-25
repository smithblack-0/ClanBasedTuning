# Milestone 2 gates — evolutionary subsystem

Status: proposed completion gates pending Milestone 1 acceptance

## Milestone result

ClanBasedTuning has an independently invokable, tested, documented, and
inspectable evolutionary controller that expresses the population-decision side
of Clan Tuning with the narrowest reasonable PBT-like responsibility. Its chosen
framework integration form is justified by direct evidence rather than assumed
in advance.

## Capability and responsibility gates

### M2.1 The controller implementation form is chosen deliberately

The milestone compares a narrow specialization of an existing Ray PBT scheduler
with an independent controller plus the thinnest viable Ray adapter. The accepted
design records:

- the exact framework seam each option requires;
- which ordinary Tune lifecycle behavior remains native;
- the version-sensitive surface and maintenance cost;
- how the public controller remains independently invokable;
- why the selected option is more coherent, concise, and maintainable.

The choice is made before later work builds around one option. A private seam is
not rejected merely because it is private, and an existing PBT class is not
adopted merely because it already exists.

### M2.2 The public population-decision contract is complete

The controller consumes one complete population result containing the member
identity, comparable fitness, current optimizer configuration, and only the
additional policy state the accepted design requires.

It produces one inspectable decision containing:

- the sole winning member whose model parameters, optimizer state, and optimizer
  configuration become the basis of the next generation;
- one legal optimizer configuration for every next-generation member;
- the member-to-parent relationship and policy information needed to explain the
  transition.

The output describes a population decision for framework-owned execution. It
does not transfer model state, construct optimizers, run training, or manage
trials.

### M2.3 Selection and optimizer configuration generation are deterministic and valid

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

The controller retains only state required to reproduce its accepted policy and
integrate through the chosen framework seam. It does not mirror trial runtime,
checkpoint contents, resource state, or experiment persistence owned by Ray Tune
or Lightning.

### M2.5 Incomplete populations do not produce valid transitions

The controller refuses to manufacture a partial evolutionary decision from a
missing or invalid population. Failure ordering and persistence are exercised to
the extent required by the chosen controller seam; process termination and
operational recovery are not controller subsystems.

## Test gates

### M2.6 Focused tests prove the public policy contract

The controller suite covers ranking modes, ties, invalid fitness, duplicate and
incomplete populations, sole-parent selection, complete optimizer-configuration
output, optimizer-only boundaries, determinism, intentional state persistence,
and inspectable decision records.

### M2.7 Framework-contract tests prove the selected seam and nothing broader

Version-specific tests invoke the real chosen Ray extension or adapter boundary
and prove that it supplies the controller's required input and can carry its
result without substantial Tune lifecycle duplication.

The claim is limited to controller integration. Trial checkpoint assignment,
Lightning restoration, DDP reformation, and continued training become
end-to-end requirements in Milestone 3.

Exact versions belong to reproducible test environments. Package dependency
constraints may claim only the compatibility range those tests establish.

### M2.8 The controller remains independently invokable

The same public controller contract can be exercised directly from explicit
population results and optimizer configurations. A framework adapter does not
become the only route to policy testing, explanation, or reuse.

## Documentation gates

### M2.9 Controller documentation transfers the complete policy model

The milestone delivers:

- the accepted controller design and the option analysis behind it;
- public API and configuration reference;
- selection, tie, mutation, retention, state, and failure semantics;
- the chosen framework seam, version assumptions, and evidence that would reopen
  the design;
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

Implementation, focused tests, framework-contract tests, design and API
documentation, decision records, and example describe one public controller
contract. Human review applies the standing framework-native review and records
the selected implementation form or any reopened assumption.

### M2.12 Milestone 3 receives a complete integration handoff

The handoff states:

- the population-result fields and completeness conditions the controller
  consumes;
- the transition decision it produces;
- intentional controller state and persistence requirements;
- the exact selected Ray seam or adapter;
- the framework responsibilities that remain outside the controller;
- the point where Milestone 3 connects the decision to training, evaluation,
  checkpoint assignment and restoration, data, resources, and distributed
  execution.

## Closure evidence

Milestone 2 closes with links to the accepted controller-form decision,
controller design and API, focused and framework-contract test results, public
example and output, decision-record reference, human review, and Milestone 3
handoff.
