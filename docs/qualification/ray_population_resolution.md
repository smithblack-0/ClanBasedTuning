# Ray population-resolution qualification

Status: active qualification boundary with initial CPU/GLOO evidence  
Framework basis: Ray 2.56.1, PyTorch 2.10.x

## Purpose

This document states what the initial Ray population-resolution implementation must prove
before the project claims a path works and records the evidence currently established.

This is an evidence boundary, not architecture. An untested topology is not forbidden;
it is unsupported until equivalent evidence exists.

## Current qualified component path

The retained framework contract currently qualifies this internal component path:

- one local Ray instance;
- two or three concurrently resident Ray actors;
- one process per stable member;
- one persistent Ray GLOO collective group;
- CPU `torch.float64` fitness payloads;
- explicit stable-member-to-collective-rank association;
- repeated all-gather boundaries for unchanged membership; and
- local actor exit when a required participant omits an all-gather beyond the configured
  timeout.

This evidence qualifies the population runtime as an internal component. It does not yet
qualify the public worker factory, Tune trial construction, checkpoint publication, the
CBT scheduler, Lightning/DDP interaction, or a complete Clan generation.

## Current retained evidence

The Ray framework contract proves:

- all three actors receive one complete stable-member-keyed population;
- collective rank order may differ from stable member order;
- adjacent Python `float64` values survive transport without collapsing into a tie;
- minimizing and maximizing modes produce the same deterministic worker decision;
- exact ties choose the lower stable member ID;
- repeated controller queries do not perform another collective operation;
- two consecutive population boundaries complete through the same initialized group; and
- when one member does not enter the all-gather, the blocked actor exits and Ray surfaces
  actor failure rather than the worker reporting a partial-population result.

Framework-independent controller tests additionally prove rejection of missing, extra, or
non-finite population values before a decision is cached.

## Required qualification paths

Every backend, device, topology, and lifecycle the implementation claims to support must
be exercised directly through real multi-process communication.

A CPU result does not qualify CUDA. An isolated actor test does not qualify Tune worker
construction. Documentation or source inspection does not qualify executable behavior.

When hosted CI cannot exercise a claimed accelerator path, a retained harness and its
reviewable output provide that evidence.

## Membership and identity evidence

A supported path proves that:

- the collective group contains exactly the configured live members;
- every stable member maps to exactly one collective participant;
- every collective participant maps back to exactly one stable member;
- gathered fitness is associated with the correct stable member rather than merely
  appearing in a plausible order; and
- changed participant ordering still produces correct identity association.

The initial CPU/GLOO component satisfies these points for fixed membership.

## Selection agreement evidence

Before the complete integration is accepted, evidence must prove that:

- every successful worker receives complete member-associated fitness;
- every worker applies the same shared selection implementation;
- every worker selects the same stable member;
- the CBT Tune scheduler independently selects that same member;
- stable tie behavior is identical on worker and scheduler paths; and
- transport conversion does not change the selected member for supported fitness values.

The current component evidence establishes worker agreement, tie behavior, and float64
transport. Scheduler agreement remains unimplemented and unqualified.

## Lifecycle evidence

A supported worker path proves that:

- one local fitness is accepted per controller boundary;
- the first save-decision query performs one population operation;
- repeated save-decision queries perform no second operation;
- later provenance work reads the cached decision rather than repeating communication;
- losing and unresolved workers cannot report a continuation checkpoint; and
- consecutive generation boundaries complete in order without exchanging values across
  generations.

The current component evidence establishes the controller and repeated-group portions.
Checkpoint reporting and provenance ordering remain unqualified.

## Failure evidence

The complete supported path must exercise at least:

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

The current CPU/GLOO evidence establishes actor exit for an omitted participant and local
validation for malformed semantic results. It does not yet establish peer failure during
an in-progress complete operation, initialization-failure release, checkpoint
suppression, or scheduler population release.

## Ray 2.56.1 timeout finding

Direct source inspection and execution show that Ray 2.56.1's GLOO `gloo_timeout`
bounds rendezvous metadata waiting but is not passed into the underlying torch collective
operation. A missing participant can therefore block an initialized all-gather beyond
that timeout.

The current runtime adds its own operation boundary. It runs all-gather on a daemon
thread and exits the current actor if the operation remains blocked. The retained test
requires Ray to surface `RayActorError` within the outer test deadline.

This evidence supports the current workaround only for the qualified actor path. It does
not establish that every future Tune or Lightning process arrangement can use the same
mechanism unchanged.

## Checkpoint and scheduler evidence

The complete integration evidence must prove that:

- exactly the worker selected through population resolution retains and reports the
  checkpoint;
- the CBT Tune scheduler independently selects the same member from reported results;
- a missing, extra, or losing checkpoint is rejected;
- producer provenance matches the selected member and active controlled optimizer
  configuration; and
- every next-generation member receives the same accepted continuation.

None of these checkpoint or scheduler claims is established by the current component PR.

## Initial non-claims

Unless separately qualified, the implementation does not claim support for:

- CUDA or NCCL population transport;
- elastic membership or world-size changes;
- mixed CPU and CUDA participants within one collective group;
- multiple independent Clan populations sharing one worker process;
- multiple collective participants inside one member process;
- public factory construction inside a Tune function;
- Lightning/DDP interaction;
- model sharding or FSDP interaction;
- arbitrary third-party collective backends; or
- recovery that resumes the same failed collective operation.

These are qualification limits, not architectural prohibitions.

## Evidence record

Current retained CI evidence uses:

- Ray 2.56.1;
- PyTorch 2.10 CPU;
- GLOO;
- two- and three-member actor groups;
- stable-member order `(2, 0, 1)` for the identity test;
- CPU `float64` scalar payloads;
- a 1,000 ms runtime timeout for omitted-participant failure; and
- `python -m pytest -m requires_ray -vv` through the repository's Ray contract job.

Every future support expansion records the exact framework versions, backend, device,
member count, resource assignment, identity mapping, timeout behavior, command or
harness, result, and intentionally withheld claims.
