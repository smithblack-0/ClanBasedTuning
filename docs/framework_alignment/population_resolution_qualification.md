# Population-resolution qualification boundary

Status: proposed Milestone 3 evidence boundary  
Date: 2026-07-31  
Framework basis: Ray 2.56.x

## Purpose

This document states what the first Ray population-resolution implementation must prove
before the project claims that path works.

This is an evidence boundary, not architecture. An untested topology is not forbidden;
it is unsupported until equivalent evidence exists.

## Required qualification paths

The initial implementation must be exercised through real multi-process Ray collective
groups with at least two live Clan members.

The evidence set must include:

1. a CPU collective path using a Ray-supported CPU backend; and
2. a CUDA collective path using a Ray-supported GPU backend for the intended GPU training
   configuration.

A CPU-only CI run is insufficient evidence for the CUDA path. When hosted CI has no
suitable accelerator, the CUDA qualification must run in a dedicated GPU harness and
retain its configuration and output as reviewable evidence.

Qualification does not require every possible Ray backend, device count, or topology.
It must cover the paths the project claims to support.

## Membership and identity evidence

Tests must prove that:

- the collective group contains exactly the configured live members;
- every stable member is mapped to exactly one collective participant;
- every collective participant maps back to exactly one stable member;
- gathered fitness is associated with the correct stable member rather than merely
  appearing in a plausible order; and
- a changed member ordering still produces correct identity association.

The implementation may use rank equality internally, but the evidence must prove the
mapping rather than assume it.

## Selection agreement evidence

For minimizing and maximizing modes, tests must prove that:

- every successful worker receives complete member-associated fitness;
- every worker applies the same shared selection implementation;
- every worker selects the same stable member;
- the scheduler independently selects that same member;
- stable tie behavior is identical on worker and scheduler paths; and
- transport conversion does not change the selected member for supported fitness values.

The evidence should include ordinary distinct fitness, an exact tie, negative values,
and values near enough to expose an unsafe transport cast.

## Lifecycle evidence

Tests must prove that:

- one local fitness is accepted per controller boundary;
- the first save-decision query performs one population operation;
- repeated save-decision queries perform no second operation;
- a later winner-only provenance check reads the cached decision;
- losing and unresolved workers cannot annotate or report a checkpoint; and
- two consecutive generation boundaries complete in order without exchanging values
  across generations.

## Failure evidence

The real Ray path must exercise at least:

- a member that never enters the population operation;
- a member that fails while peers are waiting;
- collective initialization failure;
- malformed or incomplete gathered output at the runtime boundary; and
- invalid local or gathered fitness.

Each case must demonstrate that:

- no checkpoint source is accepted;
- no member reports a continuation checkpoint;
- waiting work is released through a surfaced failure rather than hanging indefinitely;
- the Clan does not continue with a reduced population; and
- no next generation is released.

Backend-specific timeout or failure behavior may differ. The qualification record must
state how each supported backend satisfies the common failure outcome.

## Checkpoint and scheduler evidence

The complete integration evidence must prove that:

- exactly the worker selected through population resolution retains and reports the
  checkpoint;
- the Tune scheduler independently selects the same member from reported results;
- the scheduler rejects a missing, extra, or losing checkpoint;
- producer metadata matches the selected member and active genome; and
- every next-generation member receives the same accepted continuation.

A fake callback or single-process controller test may support local unit coverage, but it
is not evidence for collective membership, failure release, device support, or
cross-generation ordering.

## Initial non-claims

Unless separately qualified, the first implementation does not claim support for:

- elastic membership or world-size changes;
- mixed CPU and CUDA participants within one collective group;
- multiple independent Clan populations sharing one worker process;
- multi-GPU collective calls within one member process;
- model sharding or FSDP interactions;
- arbitrary third-party Ray collective backends; or
- recovery that resumes the same failed collective operation.

These are qualification limits, not architectural prohibitions. Adding support requires
new evidence and may require a new implementation decision, but it does not automatically
reopen the population-resolution invariants or responsibility boundaries.

## Evidence record

The implementation PR must identify:

- the exact Ray version;
- backend and device for each test path;
- member count and resource assignment;
- the stable member-to-participant mapping;
- timeout and failure configuration;
- commands or harness used;
- pass/fail output; and
- any support claim intentionally withheld.
