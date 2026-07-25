# Milestone 5 gates — optimizer utility

Status: proposed future milestone gate under Milestone 1 review

## Milestone result

ClanBasedTuning applies evolved optimizer configurations predictably across
realistic optimizer, parameter-group, and multi-optimizer layouts through one
documented, tested, and inspectable resolution model.

This gate states the required utility result and major evidence. Detailed rule
and type design is produced when Milestone 5 becomes active.

## Capability and responsibility gates

### M5.1 Optimizer configuration application has one explicit owner

The `OptimizerAdapter` system, or an accepted replacement, is the sole owner of
mapping evolved configuration values onto already constructed optimizers. It
does not construct optimizers, reinterpret the complete Tune configuration, or
compete with Lightning's optimizer lifecycle.

### M5.2 Default and targeted mapping are predictable

The accepted model provides direct same-name mapping by default and may support
explicit remapping and targeting by optimizer, optimizer type, or parameter
group. Any precedence rule is deterministic and documented. Unsupported,
ambiguous, or unapplied declarations fail clearly rather than being silently
ignored or leaked to unrelated optimizers.

### M5.3 The utility preserves inherited optimizer state

In the real Clan lifecycle, evolved values are applied after the parent optimizer
state has been restored. Supported momentum, moment, counter, parameter-group,
multi-optimizer, and scheduler interactions remain coherent; competing authority
is rejected or explicitly integrated.

### M5.4 The abstraction remains concise and auditable

Every rule or type establishes a necessary public contract or removes genuine
repeated logic. A reader can predict the result without reading framework
internals or learning a second experiment configuration language.

## Test and evidence gates

### M5.5 Focused tests prove the resolution model

The test suite covers direct mapping, remapping, targeting, deterministic
specificity, ambiguity, invalid values, unchanged unrelated optimizers or groups,
and failure for declared values that cannot be applied.

### M5.6 Integration tests prove realistic layouts

Using the public Clan workflow, integration evidence covers representative
optimizer types, multiple parameter groups, the supported multi-optimizer forms,
and application after parent-state inheritance with optimizer history preserved.
The exact supported envelope follows the evidence rather than an aspirational
matrix.

## Documentation gates

### M5.7 Reference documentation makes every result predictable

The milestone delivers a conceptual guide, complete mapping and precedence
reference, worked resolution examples, lifecycle and scheduler guidance,
extension guidance, support limits, and troubleshooting. A reader can determine
where every declared value goes and what failure to expect without source
inspection.

## Example and scientific-work gates

### M5.8 Public examples demonstrate realistic optimizer layouts

Executable examples use the public package to demonstrate parameter-group and
multi-optimizer application, remapping or targeting, lifecycle placement after a
normal parent-state transition, and at least one unsupported or ambiguous case
with its failure explanation.

### M5.9 An optimizer-policy study uses the complete public system

At least one reproducible study tunes realistic optimizer-side values over
multiple rounds, records candidate configurations, selected policy path,
fitness, training behavior, compute cost, and limitations, and reports favorable,
neutral, or unfavorable findings honestly.

## Review and handoff gates

### M5.10 The utility products agree

Resolution code, focused and integration tests, reference documentation,
troubleshooting, examples, and the optimizer-policy study use one public rule
model. Human review confirms that the utility has not become an optimizer factory
or package-wide experiment schema.

### M5.11 Milestone 6 receives a directly qualified optimizer envelope

The handoff identifies the optimizer types, group forms, scheduler interactions,
precision modes, lifecycle placement, diagnostics, and material state or
performance costs directly established by evidence.

## Closure evidence

Milestone 5 closes with the accepted resolution design, focused and integration
tests, guide and reference documentation, realistic examples, optimizer-policy
study and artifacts, human review, and Milestone 6 handoff.
