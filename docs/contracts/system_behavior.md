# Clan Tuning system behavior

Status: accepted behavioral contract

## Purpose

This contract states the observable behavior a complete public integration must produce.
It does not prescribe framework hooks, internal classes, checkpoint metadata
representation, or a support matrix.

## 1. One common inherited continuation

At the beginning of a generation, every member receives the selected parent's model
state, optimizer history, and training progress. No losing continuation is mixed into any
member.

Every member also receives its own next genome. That genome is an independent mutation of
the selected parent's genome, including for the member that won the preceding generation.

Genome application belongs to user code. A valid userspace application preserves whatever
inherited state the user intends to retain and changes only what the user's genome logic
chooses to change. CBT does not infer or perform this application.

## 2. Shared training work with member-side variation

Every required member contributes its local training work to the common gradient for the
supported distributed path. Corresponding trainable parameters receive the same reduced
gradient before each member performs its local update.

Each member then updates through its own local state and the choices represented by its
current genome. For ordinary Clan Tuning this is optimizer-side variation. Differences
between supported configurations therefore produce the intended member divergence without
a later framework operation silently erasing it.

## 3. Comparable member-local fitness

Every member is evaluated at the same logical training boundary on an equivalent held-out
workload using the same metric definition.

Fitness is computed from that member's local candidate state and remains associated with
that member. Distributed metric reduction must not collapse the distinct candidate values
that Clan selection needs to compare.

A support claim for a concrete data-loading path must establish that its evaluation
workloads are actually comparable; merely reaching validation at the same time is not
sufficient.

## 4. One selected continuation

A valid generation selects exactly one member. The continuation used for the next
generation must match that member's model state, optimizer history, and training progress
at the evaluated boundary.

No losing state is averaged, merged, or loaded into the next generation. The Tune-side
transition must have enough mechanically established source identity to verify that the
accepted continuation came from the selected member. This does not require duplicating the
parent genome inside the Lightning checkpoint when the scheduler already owns that Tune
config.

## 5. Complete next-generation assignment

Every next member receives the same selected training continuation and its own independently
mutated genome derived from the selected parent's genome.

The complete population assignment must be coherent: no child starts from a losing
checkpoint, another child's mutated genome, or a parent from a different generation.
Selection, checkpoint assignment, and child-genome production together define one logical
generation transition.

How the receiving program uses each supplied genome remains userspace and is not part of
CBT's application machinery.

## 6. Complete population participation

A generation is valid only for the complete configured Clan. Missing, duplicated,
malformed, failed, or cross-generation participation cannot be reinterpreted as a smaller
valid population.

The pre-report population boundary additionally obeys the
[population-resolution invariants](population_resolution_invariants.md).

Failure and recovery support is qualification-specific. An unsupported failure mode may
fail the experiment rather than recover, but it must not intentionally convert known
partial participation into a valid winner.

## 7. Repeated operation

The supported integration must complete successive generations through the same public
path. A one-off state transfer, synthetic callback, or isolated policy test is not
evidence that the complete Clan Tuning lifecycle works.

For a function-trainable path, repeated-operation evidence includes the receiving user
function actually seeing both the selected checkpoint and its newly assigned genome, with
userspace application remaining outside CBT.

## Evidence boundary

Focused tests may establish individual mechanisms. Acceptance of a complete integration
requires a real multi-member Ray Tune and Lightning/PyTorch run that observes the
behaviors above over repeated generations.

Backend, device, topology, precision, optimizer layout, evaluation-data arrangement,
recovery, and scale claims require direct evidence for the path claimed. Absence of
evidence limits support; it does not by itself prohibit another implementation.
