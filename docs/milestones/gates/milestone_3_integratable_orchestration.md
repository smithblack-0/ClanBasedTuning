# Milestone 3 gates — integratable orchestration subsystems

Status: proposed future milestone gate

## Milestone result

The accepted evolutionary controller and Clan-specific integration primitives can
be manually composed into a real distributed Lightning workflow in which Clan
Tuning completes multiple rounds end to end through native Ray Tune, Lightning,
and PyTorch behavior.

This gate states the required result and major evidence. The detailed integration
design and test matrix are produced when Milestone 3 becomes active.

## Capability and responsibility gates

### M3.1 The Ray invocation form is chosen deliberately

Milestone 3 uses direct framework evidence to choose the narrowest coherent way
for Ray Tune to collect one complete population result, invoke the accepted
controller once, and execute the returned transition. The design may use a narrow
PBT specialization, another scheduler boundary, or a thin adapter, but it must
justify the selected form against native lifecycle ownership, version-sensitive
surface, maintenance cost, and the risk of duplicating Tune controller behavior.

The choice adapts Ray to the accepted controller contract. It does not redefine
the controller around the selected hook.

### M3.2 The manual workflow preserves native ownership

The workflow explicitly composes the accepted controller, Ray trial execution,
Lightning training and validation, PyTorch distributed execution, model and
optimizer construction, data configuration, and only the Clan-specific seams
shown necessary by evidence.

It introduces no second training loop, population runtime, checkpoint system,
data framework, or gradient-collective implementation.

### M3.3 One coherent live population performs shared-gradient training

The manual composition verifies that the complete trial population, concurrent
resources, Clan membership, and distributed ranks describe one live Clan before
training begins. Native distributed execution produces a common gradient from
independently partitioned training batches while member-local optimizer state and
configuration produce observable divergence.

### M3.4 Lightning produces comparable round results

The integration defines the qualifying Lightning validation-and-checkpoint event.
Every live member reaches the same logical boundary, evaluates the same held-out
workload under equivalent conditions, and reports one member-local fitness value
without candidate scores being reduced together.

### M3.5 The chosen Ray integration executes the sole-parent transition

At a qualifying boundary, each candidate can provide the native trial-local
checkpoint and report required by the accepted Ray path. The accepted controller
selects one parent and next optimizer configurations; native Ray execution
assigns the resulting state/configuration; Lightning restores inherited model,
optimizer, and progress state; ClanBasedTuning reapplies receiving optimizer
values; and the next live distributed population continues training.

This is the ordinary Clan round transition, not an operational interruption-
recovery subsystem.

### M3.6 A broken active population fails collectively and clearly

A missing or failed member cannot be silently removed while the remaining
members continue as the same Clan. The supported manual workflow terminates or
invalidates the run without indefinite collective waits and exposes enough
member and lifecycle context for engineering diagnosis.

## Test and evidence gates

### M3.7 Direct and framework-contract tests protect the integration seams

Focused tests cover each Clan-specific primitive's contract, lifecycle position,
state ordering, and failure behavior. Version-specific framework-contract tests
cover the selected Ray invocation seam and only the PyTorch, Lightning, and Ray
assumptions material to the supported manual workflow.

### M3.8 End-to-end evidence proves repeated real rounds

A public manual composition with a real multi-member population completes
multiple round transitions and demonstrates shared gradients, optimizer-driven
divergence, comparable local fitness, sole-parent selection, native state
inheritance, post-restore optimizer reconciliation, distributed reformation, and
continued training.

Any accelerator or topology claim requires direct evidence on that accelerator
or topology. CPU evidence qualifies only the CPU path it exercises.

## Documentation gates

### M3.9 Engineering documentation enables manual composition and audit

The milestone delivers the accepted Ray integration-form analysis, integration
design and ownership map, manual composition guide, reference for the
Clan-specific primitives and required framework settings, tested support and
limitation statement, and failure-boundary guidance. A project engineer can
follow one complete round from training through the next generation without
reconstructing the design from source code.

## Example and scientific-work gates

### M3.10 A public mechanics example exposes the complete workflow

A reproducible example uses the public manual path, completes multiple real
rounds, and makes gradients, divergence, fitness, selected parent, resulting
optimizer configurations, state inheritance, and continued training inspectable.

### M3.11 An initial scientific workload begins evaluating the method

A public-package experiment uses a real task capable of illustrating optimizer-
policy adaptation, records its workload, round policy, fitness, compute cost,
and limitations, and reports favorable, neutral, or unfavorable results honestly.
It proves that the integrated product can investigate the method; it need not
prove that the method is valuable.

## Review and handoff gates

### M3.12 The complete manual workflow is internally consistent

Implementation, tests, framework evidence, documentation, and examples describe
one supported manual workflow. Human review applies the standing framework-native
review to the selected Ray invocation form and every other custom seam.

### M3.13 Milestone 4 receives the proven manual sequence

The handoff identifies the user-facing assembly steps that the usability
frontend may remove, the lower-level public primitives it must continue to use,
the support boundary it must preserve, and the advanced manual path that remains
available.

## Closure evidence

Milestone 3 closes with the accepted Ray integration-form decision, integration
design, direct and framework-contract tests, multi-round end-to-end evidence,
manual integration and support documentation, mechanics example, initial
scientific workload and results, human review, and Milestone 4 handoff.
