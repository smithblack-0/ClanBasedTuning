# Clan Tuning system behavior

Status: accepted behavioral contract

## Purpose

This contract states the observable behavior the complete public integration
must produce. It does not prescribe framework hooks, internal classes,
checkpoint metadata representation, or a support matrix.

## 1. One common inherited continuation

At the beginning of a generation, every member restores the selected parent's
model state, optimizer history, and training progress. No losing continuation is
mixed into any member.

Each member may then receive a different optimizer configuration. Applying that
configuration must preserve the inherited optimizer history and must not alter
unrelated model or training-progress state.

## 2. Shared training work with optimizer-side variation

Every required member contributes its local training work to the common gradient
for the supported distributed path. Corresponding trainable parameters receive
the same reduced gradient before local optimizer application.

Each member applies that gradient through its own optimizer state and assigned
optimizer configuration. Differences between supported configurations therefore
produce the expected member divergence without a later framework operation
silently erasing it.

## 3. Comparable member-local fitness

Every member is evaluated at the same logical training boundary on an equivalent
held-out workload using the same metric definition.

Fitness is computed from that member's local model state and remains associated
with that member. Distributed metric reduction must not collapse the distinct
candidate values that Clan selection needs to compare.

## 4. One selected continuation

A valid generation selects exactly one member. The continuation reported for the
next generation must match that member's model state, optimizer history, and
training progress at the evaluated boundary.

No losing state is averaged, merged, or loaded into the next generation. The
reported continuation must carry enough producer provenance for the Tune-side
transition to verify its source.

## 5. Complete next-generation assignment

Every next member receives the same selected training continuation and its own
assigned optimizer configuration. No next member starts until the complete
population assignment is ready.

The selection, mutation, checkpoint assignment, and target configurations must
form one coherent transition. A crash or failure may restore the last completed
transition or fail the experiment; it must not release a mixed generation.

## 6. Complete population participation

A generation is valid only for the complete configured Clan. Missing, duplicated,
malformed, failed, or cross-generation participation cannot be reinterpreted as a
smaller valid population.

The pre-report population boundary additionally obeys the
[population-resolution invariants](population_resolution_invariants.md).

## 7. Repeated operation

The supported integration must complete successive generations through the same
public path. A one-off state transfer, synthetic callback, or isolated policy test
is not evidence that the complete Clan Tuning lifecycle works.

## Evidence boundary

Focused tests may establish individual mechanisms. Acceptance of the complete
integration requires a real multi-member Ray Tune and Lightning/PyTorch run that
observes the behaviors above over repeated generations.

Backend, device, topology, precision, optimizer-layout, recovery, and scale claims
require direct evidence for the path claimed. Absence of evidence limits support;
it does not by itself prohibit another implementation.
