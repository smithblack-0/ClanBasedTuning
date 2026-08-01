# Initial population-resolution implementation

Status: accepted initial implementation decision and qualification boundary  
Framework basis: Ray 2.56.x

This document records the first implementation chosen to satisfy the accepted [`population-resolution contract`](../contracts/population_resolution.md). It is replaceable without reopening architecture when a replacement preserves the contract and is qualified directly.

## Chosen mechanism

The first Ray population runtime uses `ray.util.collective.allgather`.

Each live member contributes one scalar fitness through one Ray collective group spanning the complete active Clan. The worker integration retains an explicit association between stable member identity and collective participation.

Each participant:

1. converts its local fitness into a backend-supported one-element transport buffer;
2. performs one all-gather into one receive element per participant;
3. converts transport order into the semantic stable-member-to-fitness association; and
4. returns the complete association to `ClanController`.

The controller applies the shared `select_winner_id()` policy and caches whether its local member is the checkpoint source. The Ray runtime does not select the winner.

## Group lifecycle

The worker integration constructs the complete group and supplies:

- the configured stable member set;
- the stable-member-to-participant mapping;
- group identity;
- backend and payload placement; and
- supported timeout and failure configuration.

The Ray runtime owns group use and teardown. The controller does not call Ray group-construction APIs.

A group may be reused across generation boundaries only when the scheduler prevents release of the next generation until the current generation is accepted and the implementation prevents skipped, duplicated, failed, or misordered participation from being accepted.

## Deliberately unfrozen implementation details

The implementation may choose, as appropriate for the qualified execution path:

- GLOO or NCCL;
- CPU or accelerator payload placement;
- tensor or array library;
- transport dtype;
- internal population container;
- internal collaborator and helper names; and
- backend-specific timeout and cancellation plumbing.

These choices are defects if they can change member association, comparison validity, selected identity, failure release, or worker/scheduler agreement.

## Validation and failure

Before communication, invalid local fitness is rejected according to the shared selection policy.

After communication, the runtime or controller verifies:

- one result for every configured participant;
- a complete one-to-one association with stable members; and
- fitness valid for the shared comparison policy.

Initialization failure, participant failure, collective failure, timeout, malformed output, or incomplete identity association fails the complete boundary. The same failed collective is not retried as though the original population remained valid; recovery belongs to the enclosing scheduler and experiment lifecycle.

## Required qualification paths

The implementation must be exercised through real multi-process Ray collective groups with at least two live members.

The initial evidence set includes:

1. a CPU collective path through a Ray-supported CPU backend; and
2. the intended CUDA collective path through a Ray-supported GPU backend.

CPU-only CI does not qualify the CUDA path. When hosted CI lacks a suitable accelerator, a dedicated GPU harness must retain its configuration and output as reviewable evidence.

## Identity and membership evidence

Tests prove:

- the group contains exactly the configured live members;
- each stable member maps to exactly one participant and vice versa;
- gathered fitness is associated with the correct stable member;
- changed participant ordering does not change semantic identity; and
- equality between member ID and rank, when used internally, is proven rather than assumed.

## Selection evidence

For minimizing and maximizing modes, tests prove:

- every successful worker obtains complete member-associated fitness;
- every worker uses the shared selection implementation;
- all workers select the same stable member;
- the scheduler independently selects the same member;
- deterministic tie behavior agrees; and
- supported transport conversion cannot change the selected member.

Cases include ordinary distinct values, exact ties, negative values, and values close enough to expose an unsafe cast.

## Lifecycle and failure evidence

Tests prove:

- one local fitness is accepted per controller boundary;
- the first save-decision query performs one population operation;
- repeated queries and provenance checks perform no second operation;
- two consecutive generation boundaries do not exchange values across generations;
- a member that never enters the operation releases peers through failure rather than indefinite wait;
- actor failure, initialization failure, malformed output, and invalid fitness invalidate the boundary; and
- no failure case accepts a checkpoint source, shrinks the Clan, or releases the next generation.

Backend-specific failure mechanics may differ, but each qualified backend must satisfy the common observable result.

## Checkpoint and scheduler evidence

Complete integration evidence proves:

- exactly the selected worker retains and reports the checkpoint;
- the scheduler independently selects the same member;
- missing, extra, or losing checkpoints are rejected;
- producer metadata matches the selected member and active genome; and
- every target receives the same accepted continuation.

A fake callback or single-process controller test is useful unit coverage but is not collective, device, failure-release, or generation-order evidence.

## Initial non-claims

Without separate qualification, the first implementation does not claim support for:

- elastic membership or world-size changes;
- mixed CPU and CUDA participants in one group;
- multiple independent Clans sharing one worker process;
- multiple collective participants inside one member process;
- model sharding or FSDP interaction;
- arbitrary third-party collective backends; or
- resuming the same failed collective operation.

These are evidence limits, not architectural prohibitions.

## Evidence record

Every implementation PR that broadens support records the exact Ray version, backend, device, member count, resource assignment, identity mapping, timeout and failure configuration, harness or command, pass/fail output, and any support claim withheld.
