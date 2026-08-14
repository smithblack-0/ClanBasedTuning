# Population-resolution responsibilities

Status: accepted and implemented for the initial DDP path

## Purpose

This document assigns ownership for the population boundary defined by
[`population_resolution_invariants.md`](population_resolution_invariants.md). It fixes
semantic authority without turning internal payload types or collective calls into public
API.

## Semantic boundary

One live member contributes one local finite fitness at one qualifying round boundary.
The population operation returns the complete ordered population needed by the shared
selection rule, with position mechanically tied to stable member/rank identity by the
integration.

The population operation does not own the distributed context that carries those values.

## Complete-Clan topology

`ClanScheduler` owns the configured Clan population and assigns stable member identity to
Tune trial identity. The wrapped function runtime conveys that assignment, world size,
and rendezvous facts to the externally launched Lightning process.

For the initial path, stable member ID is deliberately the corresponding DDP global rank.
That makes the result position returned by the framework collective an established member
association rather than an incidental list order.

The complete population must be concurrently resident. The runtime does not reinterpret
an incomplete or resource-starved population as a smaller valid Clan.

## Framework-managed distributed context

Lightning, PyTorch, and the external Tune trial process lifecycle own:

- process-group initialization and lifetime;
- backend and device behavior;
- rank and world-size realization;
- DDP gradient communication;
- barriers and collective execution; and
- distributed failure behavior of the qualified framework path.

The same established group carries population fitness. CBT creates no second Ray, GLOO,
NCCL, CUDA, or PyTorch collective group for selection and does not choose a backend for
that operation.

## Fitness exchange

The initial implementation performs the population exchange inside
`ClanTuneReportCallback` through `trainer.strategy.all_gather()`.

That operation owns only:

- contributing the local fitness tensor to the active strategy collective; and
- returning the complete gathered fitness vector to the controller.

It does not own minimizing/maximizing semantics, ties, winner selection, mutation,
checkpoint construction, Tune reporting, or process-group lifecycle.

Malformed population size and non-finite returned fitness are rejected by
`ClanController` before a winner is accepted.

The current framework collective itself has no CBT-specific timeout/cancellation layer.
Failure release after a distributed participant disappears remains unqualified hardening
work rather than behavior the initial path claims to support.

## Framework-independent selection

The shared selection function owns:

- comparison direction;
- deterministic tie behavior; and
- selection of one stable member from the complete fitness vector.

Workers and the Tune scheduler call the same implementation. There is no second
transport-specific winner rule.

## `ClanController`

`ClanController` owns one worker's local population-decision lifecycle:

- stable local member identity;
- expected population size and comparison mode;
- one finite local fitness;
- one invocation of the injected complete-population exchange;
- one application of the shared selection rule; and
- cached winner identity and local checkpoint-source answer.

The controller does not own genome values, genome application, optimizer state,
distributed setup, checkpoint construction, Tune reporting, mutation, or generation
advancement.

Ordinary Lightning/Tune users do not construct the controller in the initial function
path. `ClanTuneReportCallback` supplies the active framework exchange internally. Direct
construction remains a framework-independent primitive for tests or advanced composition.

## Worker runtime

The hidden runtime created by `ClanScheduler.wrap(train)` owns only the information that
separate Tune trials need in order to form one externally launched Lightning DDP world:

- trial-to-stable-member assignment;
- population size;
- comparison metric and mode needed by reporting;
- rendezvous address and port; and
- per-invocation cohort synchronization.

It has no genome field and does not inspect the function's config argument. The user
function receives the original Ray config unchanged.

## `ClanTuneReportCallback`

The reporting callback owns the bridge from a qualifying Lightning validation boundary to
Tune:

1. read the configured local Lightning metric;
2. exchange one fitness per member through the active strategy;
3. resolve the worker winner with `ClanController`;
4. scope Lightning's checkpoint write to that winner while every rank participates in the
   checkpoint barrier; and
5. report ordinary metrics from every trial and a Ray checkpoint only from the winner.

The callback has no genome-application responsibility.

## `ClanScheduler`

`ClanScheduler` is a synchronous Ray `PopulationBasedTraining` specialization and is the
Tune-side evolutionary authority.

It owns:

- complete stable-member assignment;
- verification that all reports describe one complete population boundary;
- independent winner selection and worker/scheduler agreement;
- verification of the single reported checkpoint source;
- snapshotting the selected parent's Tune config;
- one independent mutation for every next member, including the selected member; and
- the mutation random stream.

Ray's native synchronous PBT lifecycle owns actual pause/checkpoint transfer/config
replacement/restart mechanics. The scheduler does not create another trial lifecycle to
perform those operations.

The scheduler does not verify genome meaning or application. The selected parent config
is already scheduler-owned Tune state; duplicating it into the Lightning checkpoint is
not required by the implemented transition.

## Lightning and PyTorch

Lightning owns training and validation cadence, full-state checkpoint construction and
restoration, strategy lifecycle, and the distributed checkpoint barrier. PyTorch DDP owns
the common-gradient execution of the initial path.

Every rank participates in the CBT round checkpoint call because Lightning's
`Trainer.save_checkpoint()` is collective. `ClanDDPStrategy` changes only which selected
rank delegates that one scoped checkpoint to `CheckpointIO`; the Trainer barrier remains
framework-owned and unchanged.

## User code

User code owns every interpretation and application of the genome supplied by Ray Tune.
Neither population resolution nor any other CBT component may infer an optimizer mapping
from genome keys or arrange application on the user's behalf.

## Failure ownership

Each layer rejects the facts it can establish:

- `ClanController` rejects invalid local lifecycle or malformed population values;
- the scheduler rejects incomplete, duplicated, cross-boundary, or inconsistent Tune
  reports;
- Lightning/PyTorch surface distributed and checkpoint-construction failures; and
- the hidden runtime times out if the complete assigned cohort never reaches its
  rendezvous.

No layer may convert a known failure into a valid partial-population winner. Bounded
recovery after a member disappears inside an active framework collective is not yet a
qualified support claim.
