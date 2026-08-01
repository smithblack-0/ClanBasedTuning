# Population-resolution invariants

Status: accepted architectural contract

## Purpose

This document defines the behavior that must remain true when the live Clan decides
which member may retain and report the generation checkpoint.

These invariants constrain every implementation. They do not prescribe a Ray backend,
tensor device, dtype, container type, class name, timeout value, or exact collective
primitive unless that choice changes the behavior below.

## Population boundary

1. One live Tune trial represents one stable Clan member.
2. The complete configured Clan participates in one population-resolution boundary for
   each qualifying generation boundary.
3. Every required member contributes exactly one local fitness produced at that same
   logical training boundary.
4. Each contributed fitness remains associated with the correct stable member.
5. A successful boundary contains one valid contribution from every required member and
   no contribution from another generation.

The population-resolution path uses Ray collective communication. PyTorch distributed
training remains responsible for training-gradient communication and is not substituted
for this Clan-level boundary.

## Selection result

A successful boundary must provide enough complete member-associated fitness information
for the shared framework-independent selection policy to identify one stable member.

The selection policy defines:

- minimizing or maximizing behavior;
- rejection of fitness values that are invalid for comparison;
- deterministic tie behavior; and
- the selected stable member identity.

Every successful worker must reach the same selected-member conclusion before any worker
reports its result to Tune.

Exactly one worker may retain and report the generation checkpoint. Every other worker
reports metrics without a checkpoint.

## Local decision lifecycle

The worker-side controller stores one local fitness and resolves one local answer to:

> Is this stable member the selected checkpoint source?

The first save-decision query may enter the Ray population-resolution boundary. Once the
answer is known, the controller caches it. Repeated queries and later producer-provenance
checks read the cache and do not perform population communication again.

## Failure and generation isolation

The boundary is invalid if any required member is missing, fails, contributes more than
once, contributes malformed fitness, or participates under the wrong generation.

An invalid boundary must not:

- select from a partial population;
- silently shrink the Clan;
- let any worker report a continuation checkpoint;
- release a next-generation member; or
- leave healthy participants waiting forever without a surfaced failure.

The concrete timeout, cancellation, exception, and generation-token mechanisms belong to
implementation and qualification work. Their observable result must satisfy this failure
invariant.

## Scheduler verification

The CBT Tune scheduler independently receives one result from every required trial,
applies the same selection policy, and verifies all of the following:

- exactly the selected member supplied a checkpoint;
- no losing member supplied a checkpoint;
- the checkpoint producer provenance matches the selected member and its active
  controlled optimizer configuration; and
- the complete next-population transition is durably accepted before any target is
  released.

Worker agreement is therefore necessary but not authoritative. The CBT Tune scheduler
remains the evolutionary authority over winner verification, mutation, child
configurations, mutation random state, lineage, recovery, target configuration, and
checkpoint redistribution.

## Representation freedom

The implementation may choose any internal representation that preserves the invariants
above. In particular, architecture does not require:

- stable member identity to equal collective rank, only an unambiguous proven mapping;
- a tuple, list, dictionary, tensor, or object as the population-fitness container;
- CPU or accelerator storage for collective payloads;
- a particular floating-point dtype;
- GLOO, NCCL, or another supported Ray collective backend;
- one specific Ray collective primitive rather than an equivalent composition;
- a specific internal collaborator, class, method, or module name; or
- one fixed timeout duration.

Those choices are safe to leave to implementation only when direct evidence shows that
they preserve complete membership, identity association, deterministic selection,
failure release, and generation isolation.
