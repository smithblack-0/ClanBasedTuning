# Milestone 4 gates — usability

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

A Lightning user can attach ClanBasedTuning through a short, documented, tested
construction path without manually assembling the surrounding DDP, model, data,
rendezvous, and plugin lifecycle. Advanced users retain the lower-level manual
composition proven in Milestone 3.

## Capability and design gates

### M4.1 The ideal user path is designed before the frontend is fixed

- The intended user sequence is written and reviewed before its manufacturing
  API becomes contractual.
- User-owned choices remain with Lightning, Ray Tune, PyTorch, and the user's
  model rather than being absorbed into a package configuration language.
- The path states what the package infers, what the user supplies, and what fails
  when the supported envelope is not met.

### M4.2 The construction path returns concrete framework components

- The frontend returns the concrete Lightning strategies, plugins, callbacks,
  samplers, or other objects the caller supplies to native framework entry
  points.
- It does not return another factory, own a Trainer, or create a parallel launch
  system.

### M4.3 DDP, model, data, and rendezvous setup are package-managed

- The simple path configures the accepted DDP behavior, model wrapping, rank and
  rendezvous information, training partitioning, comparable evaluation, and
  member-local checkpoint behavior.
- Invalid population or resource composition fails before training begins.
- Package setup remains a composition of the same primitives proven manually in
  Milestone 3.

### M4.4 Convenience remains auditable composition

- Each convenience operation delegates to the same lower-level primitives proven
  in Milestone 3.
- The manual path remains documented and usable for advanced integration.
- No convenience-only implementation diverges from the composable path.

### M4.5 The supported user envelope is explicit

- Supported Lightning, Ray, PyTorch, topology, loader, precision, optimizer, and
  stopping assumptions are stated in user-facing documentation.
- Unsupported configurations fail clearly rather than silently degrading Clan
  semantics.

## Test gates

### M4.6 Construction-unit tests prove what the frontend assembles

Tests verify:

- the concrete component types and settings returned for each supported setup;
- correct propagation of user-owned Trainer, model, optimizer, and Tune choices;
- DDP, rendezvous, sampler, callback, checkpoint, and report configuration;
- preflight rejection of invalid population, concurrency, device, or unsupported
  configuration;
- absence of a package-owned Trainer, hidden launch loop, or duplicate framework
  lifecycle.

### M4.7 Public quickstart integration tests prove the ordinary path

The documented short path completes the same multi-round lifecycle proven in
Milestone 3, including shared gradients, divergence, comparable fitness,
selection, restoration, and continuation.

- Tests use only the public quickstart construction path and ordinary framework
  entry points.
- The result is compared against the lower-level manual path for the same
  supported configuration.
- Convenience and manual composition produce equivalent Clan behavior and
  transition records.

### M4.8 Usability and failure tests cover the reader-facing experience

- Every documented setup error has an actionable, tested failure message.
- A fresh-user walkthrough follows the published guide in a clean environment
  without undocumented setup or source inspection.
- Installation, configuration, first run, expected output, and common failure
  recovery are exercised as one user journey.
- The walkthrough records friction or ambiguity as a gate failure, not as a
  future documentation cleanup item.

## Documentation gates

### M4.9 User documentation enables both ordinary and advanced paths

The milestone delivers:

- a getting-started guide from installation through the first complete Clan run;
- a concise quickstart for the ordinary construction path;
- an advanced manual-composition guide retained from Milestone 3;
- public API and configuration reference for the manufacturing frontend and
  returned components;
- a support and limitations reference covering versions, topology, data,
  precision, optimizer, stopping, restoration, and resource assumptions;
- troubleshooting guidance keyed to actual setup and lifecycle diagnostics;
- an explanation of expected output and how to inspect the Clan transition.

The guide must enable a new Lightning user to complete the supported task without
reconstructing distributed-framework internals.

## Example and scientific-work gates

### M4.10 A short public quickstart demonstrates the ordinary path

The quickstart example:

- uses the public manufacturing frontend and native Lightning/Ray entry points;
- contains no hidden manual DDP, model-wrapping, data-partitioning, rendezvous, or
  plugin setup;
- completes the supported round lifecycle;
- explains the minimum required user choices, expected records, and how to read
  the result;
- is maintained as an executable test of the documented ordinary path.

### M4.11 The advanced manual example remains valid and connected

- The Milestone 3 manual-composition example remains runnable against the same
  public primitives used by the quickstart.
- Documentation explains when an advanced integrator should use the manual path
  and which responsibilities they then own.
- The quickstart and manual example do not teach conflicting configuration or
  lifecycle models.

### M4.12 Scientific examples use the ordinary public path where practical

The initial scientific workload from Milestone 3 is migrated to or reproduced
through the ordinary construction path unless the experiment genuinely requires
advanced composition. Any remaining manual setup is explained rather than
hidden.

## Evidence, review, and handoff gates

### M4.13 The milestone products agree

- The frontend, tests, getting-started guide, references, troubleshooting, and
  examples describe one user path and one support envelope.
- Human review applies the standing framework-native review and verifies that
  usability did not introduce hidden ownership or a second implementation.
- The fresh-user walkthrough and automated quickstart test both succeed from the
  published instructions.

### M4.14 Milestone 5 receives the optimizer-utility requirements users exposed

The handoff records:

- optimizer layouts the ordinary and advanced paths currently support;
- realistic user configurations that remain awkward, ambiguous, or unsupported;
- the public configuration values and optimizer objects the future utility must
  reconcile;
- examples and tests that Milestone 5 must extend rather than replace.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| General optimizer resolution | Milestone 5 | The usability path may support the narrow optimizer contract already proven. | Make evolved configuration application predictable across realistic layouts. | Utility tests, reference documentation, realistic public examples, and optimizer-policy study. |
| Production-scale observability, sharding, and cluster recovery | Milestone 6 | The simple path is qualified for its declared non-industry envelope. | Qualify serious operating environments and failure modes. | Industry readiness audit, direct failure/accelerator tests, operations docs, and scaled examples. |

## Closure evidence

Milestone 4 closes with links to the accepted user-path design, construction-unit
and quickstart integration tests, fresh-user walkthrough, getting-started and
advanced guides, API/support/troubleshooting references, quickstart and manual
examples, migrated scientific workload, review result, and Milestone 5 handoff.
