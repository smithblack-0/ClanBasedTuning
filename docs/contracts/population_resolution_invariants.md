# Population-resolution invariants

Status: accepted architectural contract

## Purpose

This document defines the behavior that must remain true when the live Clan decides which
member may retain and report a generation checkpoint. It constrains semantics without
prescribing a backend, payload dtype, container type, timeout mechanism, or exact
collective primitive.

## Population boundary

1. One live Tune trial represents one stable Clan member.
2. The complete configured Clan participates in one population-resolution boundary for
   each qualifying generation boundary.
3. Every required member contributes exactly one finite local fitness produced at that
   same logical training boundary.
4. Each contributed fitness remains associated with the correct stable member.
5. A successful boundary contains one valid contribution from every required member and
   no contribution from another generation.

For the initial DDP path, population resolution uses the framework-managed distributed
context already spanning the live Clan for shared training. Population-resolution logic
does not establish, choose the backend for, or tear down another process group.

A later model-sharded Clan topology may contain more than one framework-owned process
group or process dimension. The invariant remains that the population operation uses the
appropriate already-established Clan-wide context rather than creating its own distributed
runtime.

## Selection result

A successful boundary provides enough complete member-associated fitness information for
the shared framework-independent selection policy to identify exactly one stable member.

The selection policy owns:

- minimizing or maximizing behavior;
- comparison-validity requirements;
- deterministic tie behavior; and
- the selected stable member identity.

Every successful worker reaches the same selected-member conclusion before reporting its
round to Tune. Exactly one worker may report the CBT continuation checkpoint. Every other
worker reports metrics without a checkpoint.

## Local decision lifecycle

The worker-side controller stores one local fitness and resolves one local answer to:

> Is this stable member the selected checkpoint source?

The first save-decision query may enter the framework-managed population-resolution
boundary. Once resolved, the controller caches both the selected member identity and the
local save answer. Repeated queries do not enter population communication again.

The controller has no genome or genome-application responsibility.

## Scheduler verification

The CBT Tune scheduler independently receives one result from every required trial and
applies the same selection policy. A valid scheduler boundary verifies that:

- every assigned stable member is present exactly once;
- all reports belong to the same Tune generation boundary;
- every worker reports the same winner selected independently by the scheduler;
- exactly the selected member identifies itself as the checkpoint source; and
- the selected source is the sole Ray checkpoint available for the generation transition.

The scheduler already owns the selected trial's Tune config. Correct transition behavior
does not require copying that genome into the Lightning checkpoint merely to recover it
again.

Worker agreement is therefore necessary but not the Tune-side evolutionary authority.
The scheduler owns the selected parent config, mutation random stream, next-member genome
assignment, and use of Ray's native checkpoint/config transition lifecycle.

## Next-generation invariant

Every next member receives:

- the same selected training continuation; and
- its own independently mutated genome derived from the selected parent's genome.

The selected member is also a next-generation target and is not exempt from mutation.
No child mutation may accidentally use another child's already-mutated genome as its
parent.

Genome application remains userspace. These invariants concern which genome CBT supplies,
not what the user's program does with it.

## Failure and generation isolation

A boundary is invalid if any required member is missing, fails, contributes more than
once, contributes malformed fitness, or participates under the wrong generation.

An invalid boundary must not be reinterpreted as a smaller valid Clan or intentionally
release a mixed next generation. The implementation must surface known invalid state
rather than silently choosing from a partial population.

The exact timeout, cancellation, and recovery mechanisms are qualification-dependent. The
initial implementation has a bounded pre-DDP cohort rendezvous timeout but does not yet
claim bounded recovery after a participant disappears inside an active framework
collective. Lack of that support claim does not make partial-population selection valid.

## Representation freedom

The implementation may choose any internal representation that preserves the invariants
above. In particular, architecture does not require:

- stable member identity to equal distributed rank, although the initial qualified path
  deliberately uses that mapping;
- a tuple, list, dictionary, tensor, or object as the population-fitness container;
- CPU or accelerator storage for the fitness payload;
- a particular floating-point dtype;
- one specific collective operation over the established framework-owned context;
- a specific internal collaborator, class, method, or module name; or
- one fixed timeout duration.

Those choices remain implementation details only while member association, deterministic
selection, single checkpoint authority, common-parent mutation, and generation isolation
remain mechanically established.
