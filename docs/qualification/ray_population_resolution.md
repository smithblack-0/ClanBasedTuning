# Ray population-resolution qualification

Status: accepted qualification boundary  
Framework basis: Ray 2.56.x

## Purpose

This document states what the initial Ray population-resolution implementation must prove
before the project claims a path works.

This is an evidence boundary, not architecture. An untested topology is not forbidden;
it is unsupported until equivalent evidence exists.

## Required qualification paths

The implementation must be exercised through real multi-process Ray collective groups
with at least two live Clan members.

Qualification covers every backend, device, and topology the initial implementation
claims to support. A CPU result does not qualify a CUDA path, and documentation alone
does not qualify executable behavior.

When hosted CI cannot exercise a claimed accelerator path, a dedicated retained harness
and its reviewable output provide that evidence.

## Membership and identity evidence

Tests prove that:

- the collective group contains exactly the configured live members;
- every stable member maps to exactly one collective participant;
- every collective participant maps back to exactly one stable member;
- gathered fitness is associated with the correct stable member rather than merely
  appearing in a plausible order; and
- changed participant ordering still produces correct identity association.

The implementation may use rank equality internally, but the evidence must prove the
mapping rather than assume it.

## Selection agreement evidence

For minimizing and maximizing modes, tests prove that:

- every successful worker receives complete member-associated fitness;
- every worker applies the same shared selection implementation;
- every worker selects the same stable member;
- the Tune integration independently selects that same member;
- stable tie behavior is identical on worker and Tune-side paths; and
- transport conversion does not change the selected member for supported fitness values.

The evidence includes ordinary distinct fitness, an exact tie, negative values, and
values close enough to expose an unsafe transport cast.

## Lifecycle evidence

Tests prove that:

- one local fitness is accepted per controller boundary;
- the first save-decision query performs one population operation;
- repeated save-decision queries perform no second operation;
- later provenance work reads the cached decision rather than repeating communication;
- losing and unresolved workers cannot report a continuation checkpoint; and
- consecutive generation boundaries complete in order without exchanging values across
  generations.

## Failure evidence

The real Ray path exercises at least:

- a member that never enters the population operation;
- a member that fails while peers are waiting;
- collective initialization failure;
- malformed or incomplete gathered output at the runtime boundary; and
- invalid local or gathered fitness.

Each case demonstrates that:

- no checkpoint source is accepted;
- no member reports a continuation checkpoint;
- waiting work is released through a surfaced failure rather than hanging indefinitely;
- the Clan does not continue with a reduced population; and
- no next generation is released.

Backend-specific timeout or failure behavior may differ. The qualification record states
how each supported path satisfies the common failure outcome.

## Checkpoint and Tune-side evidence

The complete integration evidence proves that:

- exactly the worker selected through population resolution retains and reports the
  checkpoint;
- the Tune integration independently selects the same member from reported results;
- a missing, extra, or losing checkpoint is rejected;
- producer provenance matches the selected member and active optimizer configuration;
  and
- every next-generation member receives the same accepted continuation.

A fake callback or single-process controller test may support local unit coverage, but it
is not evidence for collective membership, failure release, device support, or
cross-generation ordering.

## Initial non-claims

Unless separately qualified, the initial implementation does not claim support for:

- elastic membership or world-size changes;
- mixed CPU and CUDA participants within one collective group;
- multiple independent Clan populations sharing one worker process;
- multiple collective participants inside one member process;
- model sharding or FSDP interaction;
- arbitrary third-party collective backends; or
- recovery that resumes the same failed collective operation.

These are qualification limits, not architectural prohibitions. Adding support requires
new evidence and may require a new implementation decision, but it does not automatically
reopen the population-resolution contracts.

## Evidence record

Every implementation change that establishes or broadens support records:

- the exact Ray version;
- backend and device for each test path;
- member count and resource assignment;
- the stable member-to-participant mapping;
- timeout and failure configuration;
- commands or harness used;
- pass/fail output; and
- any support claim intentionally withheld.
