# Milestone 2 controller plan

Status: active execution plan  
Date: 2026-07-25

## Governing boundary

Milestone 2 delivers an independently invokable Clan evolutionary controller. The
controller owns population policy: it accepts one complete population result,
selects the sole parent, and produces the next optimizer-hyperparameter
configurations.

Milestone 2 does not choose or implement the Ray Tune invocation path. Ray trial
objects, scheduler specialization, checkpoint transfer, distributed
communication, Lightning callbacks, optimizer construction, and live optimizer
application belong to Milestone 3 or later integration work.

## Review units

The milestone proceeds through separate stable pull requests.

### 1. Controller design and lifecycle contract

Document the controller's purpose, ownership, lifecycle boundary, input and output
model, mutation geometry, randomness/state model, failure behavior, and the way a
small synthetic training loop would use it. Compare plausible designs and accept
one before implementation.

This unit contains no production controller code and makes no Ray integration
choice.

### 2. Controller implementation and focused tests

Implement only the accepted controller contract. Keep the code framework-neutral,
use ordinary data structures unless a type establishes a necessary contract, and
write focused tests for the documented preconditions, postconditions, algorithms,
state, determinism, and failure behavior.

This unit does not claim framework integration or milestone completion.

### 3. Demonstration, reference, and handoff

Add internal API/reference documentation and a reproducible pet loop that evolves
several synthetic generations from visible fitness values and optimizer
configurations. The example must show where an external training system supplies
fitness and applies the returned decision without pretending to integrate Ray or
Lightning.

Complete the Milestone 3 handoff with the accepted plain-data contract and the
framework responsibilities still outside the controller.

## Completion rule

Milestone 2 is ready for closure review only when the accepted design,
implementation, focused tests, internal reference documentation, pet-loop
example, and integration handoff describe one controller contract and satisfy the
Milestone 2 gate.

Unresolved framework integration choices remain Milestone 3 work; they are not
pulled into this plan merely because future integration will consume the
controller.
