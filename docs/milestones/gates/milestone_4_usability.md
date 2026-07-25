# Milestone 4 gates — usability

Status: proposed future milestone gate under Milestone 1 review

## Milestone result

A Lightning user can attach ClanBasedTuning through a short, documented
construction path without manually assembling the surrounding DDP, model,
distributed-data, rendezvous, reporting, and plugin lifecycle proven in
Milestone 3. Advanced users retain the lower-level manual path.

This gate states the required user result and major evidence. The final frontend
shape is designed when Milestone 4 becomes active.

## Capability and responsibility gates

### M4.1 The ideal user path is designed before the API is fixed

The intended sequence states what the user supplies, what ClanBasedTuning
assembles, which decisions remain with Lightning, Ray Tune, PyTorch, and the
user's model, and which unsupported situations fail before training.

### M4.2 The frontend returns concrete native components

The manufacturing frontend returns the actual strategies, plugins, callbacks,
samplers, adapters, or focused helpers supplied to native framework entry
points. It does not return another factory, own a Trainer, or introduce a
parallel launch or training system.

### M4.3 Convenience remains auditable composition

The short path assembles the same lower-level public primitives and lifecycle
proven in Milestone 3. Invalid population, resources, devices, or unsupported
framework combinations fail before training begins. The advanced manual path
remains documented and usable.

## Test and evidence gates

### M4.4 Construction and preflight tests prove the frontend contract

Tests establish that the frontend returns and configures the intended native
components, preserves user-owned choices, and rejects invalid setup before
expensive distributed work begins.

### M4.5 The documented short path completes the proven workflow

An end-to-end test using only the public ordinary path completes the supported
multi-round lifecycle and produces behavior equivalent to the accepted manual
composition. The usability layer does not create a second round-transition
implementation.

### M4.6 A fresh-user walkthrough proves practical usability

A technically competent Lightning user can install the package in a clean
environment, complete the first supported run, interpret its output, and resolve
common setup failures using only published material.

## Documentation gates

### M4.7 User documentation enables ordinary and advanced use

The milestone delivers a getting-started guide, concise quickstart,
construction API and configuration reference, support and limitations reference,
troubleshooting guidance, and the retained advanced manual-composition guide.
The documentation explains expected output and the responsibilities an advanced
user assumes when choosing the manual path.

## Example gates

### M4.8 The ordinary quickstart is complete and public

The quickstart uses the manufacturing frontend and native Lightning/Ray entry
points, contains no hidden manual distributed setup, completes the supported
round lifecycle, and explains the minimum user choices and observable result.

### M4.9 The advanced example remains valid

The Milestone 3 manual example continues to run against the same public
primitives. The ordinary and advanced examples teach one lifecycle and support
boundary at different abstraction levels.

## Review and handoff gates

### M4.10 The user-facing products agree

Frontend, tests, guides, troubleshooting, quickstart, and advanced example
describe one construction path and support boundary. Human review confirms that
usability has not introduced hidden framework ownership or convenience-only
behavior.

### M4.11 Milestone 5 receives evidence from real optimizer use

The handoff records the optimizer layouts supported by the ordinary and advanced
paths, the realistic layouts still awkward or unsupported, and the public
configuration and optimizer objects the utility must reconcile.

## Closure evidence

Milestone 4 closes with the accepted user-path design, construction and
end-to-end tests, fresh-user walkthrough, user and advanced documentation,
ordinary and manual examples, human review, and Milestone 5 handoff.
