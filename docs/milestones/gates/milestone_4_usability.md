# Milestone 4 gates — usability

Status: working rewrite for review

## Milestone result

A Lightning user can attach ClanBasedTuning through a short, documented construction path without manually assembling the DDP, model, data, rendezvous, and plugin lifecycle proven in Milestone 3. Advanced users retain the lower-level manual path.

## Capability and responsibility gates

### M4.1 The ideal user path is designed before its API is fixed

The intended sequence states what the user supplies, what ClanBasedTuning assembles, which decisions remain with Lightning, Ray Tune, PyTorch, and the model, and which unsupported situations fail before training.

### M4.2 The manufacturing frontend returns concrete framework components

The public construction function returns the actual strategies, plugins, callbacks, samplers, or focused helpers supplied to native framework entry points. It does not return another factory, own a Trainer, or introduce a parallel launch system.

### M4.3 The ordinary path removes the intended assembly ceremony

The short path configures the accepted DDP behavior, model wrapping, rank and rendezvous data, training partitioning, comparable evaluation, reporting, and trial-local checkpoint behavior by composing the same public primitives proven manually in Milestone 3.

### M4.4 Convenience and manual composition remain one implementation

The simple and advanced paths use the same underlying components and lifecycle. The manual path remains documented and usable; convenience does not hide a second implementation.

## Test gates

### M4.5 Construction and preflight tests prove the frontend contract

Tests verify returned component types and settings, propagation of user-owned choices, correct distributed/data/report configuration, and early rejection of invalid population, resources, devices, or unsupported configurations.

### M4.6 The public quickstart completes the Milestone 3 lifecycle

An end-to-end test using only the documented short construction path completes repeated Clan rounds and produces behavior equivalent to the supported manual composition. The test does not create a new round-transition contract; it proves that the convenience path assembles the existing one correctly.

### M4.7 A fresh-user walkthrough tests usability

A technically competent Lightning user follows the published installation and getting-started path in a clean environment, completes the first supported run, interprets its output, and can diagnose and correct common setup failures without source inspection or undocumented help.

## Documentation gates

### M4.8 User documentation enables ordinary and advanced use

The milestone delivers a getting-started guide, concise quickstart, construction API/configuration reference, support and limitations reference, troubleshooting guide, and the retained advanced manual-composition guide. Documentation explains expected output and which responsibilities advanced users assume when they choose the manual path.

## Example gates

### M4.9 The ordinary quickstart is complete and public

The quickstart uses the manufacturing frontend and native Lightning/Ray entry points, contains no hidden manual distributed setup, completes the supported round lifecycle, and explains the minimum choices and observable result.

### M4.10 The advanced manual example remains valid

The Milestone 3 manual example continues to run against the same public primitives. The two examples teach one lifecycle and support boundary at different abstraction levels.

## Evidence, review, and handoff gates

### M4.11 The user-facing products agree

Frontend, tests, guides, troubleshooting, quickstart, and advanced example describe one construction path and support envelope. Human review confirms that usability has not introduced hidden framework ownership or convenience-only behavior.

### M4.12 Milestone 5 receives real optimizer-utility requirements

The handoff records the optimizer layouts supported by the ordinary and advanced paths, the realistic layouts still awkward or unsupported, and the public configuration/optimizer objects the utility must reconcile.

## Closure evidence

Milestone 4 closes with links to the accepted user-path design, construction and quickstart tests, fresh-user walkthrough, user and advanced documentation, quickstart and manual examples, human review, and Milestone 5 handoff.