# Ray population-resolution design

Status: review candidate for Milestone 3  
Date: 2026-07-31

## Purpose

This document isolates the requirements for deciding which live Clan member may report
the generation checkpoint.

The architecture already commits to a Ray collective across the concurrently resident
Clan. The open work is not whether to use Ray collectives. It is to design the worker
boundary, data contract, names, and failure behavior without mistaking one provisional
callback for the architecture.

## Accepted architecture commitments

The following requirements are fixed for the current Milestone 3 design:

1. One live Ray Tune trial represents one stable Clan member.
2. The complete configured population is concurrently resident for a generation.
3. The live members use a Ray collective for the Clan-specific population-resolution
   step.
4. Every required member contributes one comparable local fitness at the same logical
   Lightning boundary.
5. The resolution identifies exactly one stable member as the checkpoint source before
   any worker reports its result to Tune.
6. Every successful participant reaches the same selected-member conclusion.
7. A worker can query its local save decision repeatedly without performing the Ray
   collective again.
8. Missing, failed, duplicated, or cross-generation participation invalidates the
   boundary. The population must not silently shrink or mix generations.
9. The Tune scheduler independently applies the same accepted selection policy to the
   completed Tune results and verifies the reported checkpoint source.
10. The scheduler remains authoritative over genomes, mutation, lineage, recovery,
    target configuration, and checkpoint redistribution.

The Ray collective exists only to let the live workers coordinate the pre-report
checkpoint source. It does not become the evolutionary policy authority.

## Intrinsic data requirements

The worker-side resolution must have enough information to apply the same deterministic
selection policy as the scheduler.

Each fitness must be associated with a stable Clan member. The implementation may prove
that Ray collective rank is identical to stable member ID, or it may communicate member
identity explicitly. Undocumented list position is not an acceptable identity contract.

The selection policy must define:

- minimizing versus maximizing;
- deterministic tie behavior;
- rejection of non-finite fitness; and
- the selected stable member ID.

The successful result exposed to a worker may be either:

- the complete member-associated fitness population, after which the shared pure policy
  selects locally; or
- the already selected stable member ID, provided the Ray-side implementation uses the
  same pure policy and every member receives the same result.

The architecture does not yet choose between those result shapes.

## Responsibility model

The design contains four distinct responsibilities. These are roles, not yet final
class or module names.

### Ray collective runtime

The Ray-specific runtime owns:

- collective-group construction and teardown;
- stable membership and rank mapping;
- one operation per logical generation boundary;
- transport and serialization;
- complete participation;
- timeout and failure release; and
- returning one consistent population-resolution result to every participant.

It must not own mutation, child-genome construction, scheduler lineage, or checkpoint
redistribution.

### Selection policy

The framework-independent evolution policy owns:

- comparison direction;
- stable tie behavior;
- fitness validation required by policy; and
- deterministic winner selection from member-associated fitness.

The worker-side path and scheduler verification must use this same policy rather than
maintaining similar implementations.

### Worker controller

The worker controller owns the user-facing boundary state:

- one local fitness value;
- participation in one population-resolution operation through the Ray integration;
- one cached local answer to whether this member is the checkpoint source; and
- later, the copied current genome and winner-only checkpoint provenance write.

The controller must not expose Ray group construction details to the training function.
The exact controller constructor and collaborator shape remain under review.

### Tune scheduler

The scheduler owns the authoritative generation transition. It independently verifies
that:

- every required trial reported;
- its selected winner matches the worker-side checkpoint source;
- exactly one checkpoint was reported;
- the checkpoint producer metadata matches the winner; and
- the next population is committed atomically before release.

## Accepted worker flow

The high-level worker ordering remains:

```text
train and evaluate one member
→ provide its local fitness to the worker controller
→ participate in one Ray population-resolution operation
→ cache whether this stable member is the checkpoint source
→ every Lightning rank enters the required checkpoint boundary
→ only the selected member retains the checkpoint
→ selected member records its member ID and copied genome in checkpoint metadata
→ report metrics, with a checkpoint only from that member
```

A later provenance check may inspect the already cached save decision. It must not invoke
a second Ray collective.

## Deliberately open implementation choices

The following choices require another implementation-oriented design review:

- which Ray collective primitive or composition is used;
- whether workers receive member-associated fitness or only the selected member ID;
- whether stable member ID is identical to Ray rank or carried explicitly;
- the exact object boundary between `ClanController` and the Ray runtime;
- the final names of that object and its operations;
- timeout configuration and surfaced failure types;
- how one generation's operation is isolated from the next; and
- the exact test harness for multi-process failure and agreement.

These choices may be constrained by direct evidence from the pinned Ray version. They
must not be decided accidentally by a convenient unit-test callback.

## Provisional current implementation

The current framework-independent controller accepts:

```python
exchange_fitness(local_fitness) -> Sequence[float]
```

and assumes sequence position is member identity.

That API is transitional evidence only. Its names, callable shape, ordering contract,
validation placement, and responsibility split are not accepted merely because the code
is merged.

The replacement must be designed from the requirements above rather than renamed in
place or copied from a rejected branch.

## Rejected shortcuts

The following approaches are insufficient without further design:

- a bare `exchange_fitness` callable with undocumented ordering;
- an opaque `local_fitness -> bool` callback that hides membership, policy, and failure
  semantics;
- reusing a collective implementation from an earlier controller architecture;
- using PyTorch DDP collectives in place of the committed Ray population collective;
- allowing every worker to save and relying on later scheduler deletion;
- allowing a partial population to select a checkpoint source; or
- duplicating the winner-selection rule in worker and scheduler code.

## Required evidence

The eventual implementation must prove, against the pinned Ray version:

- all configured members join one population-resolution group;
- stable member identity is associated correctly with every fitness;
- every member receives the same selected stable member ID;
- minimizing, maximizing, and tie behavior match the shared pure policy;
- repeated local save queries perform no second collective;
- non-finite or malformed population data fails the boundary;
- a missing participant releases waiting work through failure rather than hanging
  indefinitely;
- operations from different generations cannot mix; and
- the scheduler independently reaches and verifies the same winner.

A fake single-process callback may support controller unit tests, but it is not evidence
for the Ray collective contract.
