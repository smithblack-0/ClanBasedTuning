# Milestone 5 gates — optimizer utility

Status: working rewrite for review

## Milestone result

ClanBasedTuning applies evolved optimizer configurations predictably across realistic optimizer, parameter-group, and multi-optimizer layouts through one documented, tested, and inspectable resolution model.

## Capability and responsibility gates

### M5.1 Configuration application has one explicit owner

The OptimizerAdapter system, or an accepted replacement, is the sole owner of mapping evolved configuration values onto already constructed optimizers. It does not construct optimizers, reinterpret the complete Tune configuration, or compete with Lightning's optimizer lifecycle.

### M5.2 Default and targeted mapping are predictable

- A declared value maps to the same-named optimizer hyperparameter by default.
- Documented rules may target optimizer type, optimizer instance/reference, parameter group, and explicit remapping.
- One deterministic specificity order resolves multiple matches.
- Equal-precedence ambiguity, unsupported values, or inapplicable declarations fail clearly.
- Declared values are never silently ignored or leaked to unrelated optimizers/groups.

### M5.3 The utility works in the real Clan lifecycle

After the native parent-state transition proven in Milestone 3, the utility applies the receiving member's evolved values while preserving inherited optimizer history such as momentum, moments, and step counters. Supported LR-scheduler interactions are explicit; conflicting authority fails before training continues.

### M5.4 The abstraction remains concise and auditable

Every type or rule establishes a necessary public contract or removes genuine repeated logic. A reader can predict the result without reading framework internals or learning a second experiment configuration language.

## Test gates

### M5.5 Focused tests cover the complete resolution model

The suite covers same-name mapping, remapping, optimizer/group targeting, specificity, ambiguity, invalid values, deterministic ordering, unchanged unrelated targets, and clear failure for every unapplied declaration.

### M5.6 Integration tests cover realistic optimizer layouts

Using the public Clan workflow, tests cover representative optimizer types, multiple parameter groups, the supported multi-optimizer forms, ordinary and advanced construction paths, and application after parent-state inheritance with optimizer history preserved.

### M5.7 Regression tests protect the public rule model

Public precedence, failure semantics, mapping output, and lifecycle placement remain stable or change only through an explicit reviewed contract update.

## Documentation gates

### M5.8 The optimizer-resolution model is fully documented

The milestone delivers a conceptual guide, complete mapping/targeting/precedence reference, worked resolution tables, lifecycle-order and scheduler guidance, extension guidance, support limits, and troubleshooting. A reader can determine the destination and effect of every declared value without source inspection.

## Example and scientific-work gates

### M5.9 Public examples demonstrate realistic layouts

Executable public-package examples cover distinct parameter groups, the broadest supported multi-optimizer layout, remapping/specificity, application after a normal parent-state transition, and at least one ambiguous or unsupported declaration with its failure explanation.

### M5.10 An optimizer-policy study uses the complete public system

At least one reproducible study tunes realistic optimizer-side values over multiple rounds, records candidate configurations, selected policy path, fitness, training behavior, computation cost, and limitations, and reports favorable, neutral, or unfavorable findings honestly.

## Evidence, review, and handoff gates

### M5.11 The utility products agree

Resolution code, focused and integration tests, reference documentation, troubleshooting, examples, and study use one public rule model. Human review confirms that the utility has not become an optimizer factory or package-wide experiment schema.

### M5.12 Milestone 6 receives a directly qualified optimizer envelope

The handoff identifies the optimizer types, group forms, scheduler interactions, precision modes, lifecycle placement, diagnostics, and performance/state costs directly tested for later industry qualification.

## Closure evidence

Milestone 5 closes with links to the accepted resolution design, focused and integration tests, guides and reference, realistic examples, optimizer-policy study and artifacts, human review, and Milestone 6 handoff.