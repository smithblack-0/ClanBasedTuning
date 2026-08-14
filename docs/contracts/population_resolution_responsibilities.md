# Population-resolution responsibilities

Status: accepted architectural contract

## Purpose

This document assigns ownership for satisfying the
[population-resolution invariants](population_resolution_invariants.md).

It fixes authority boundaries where ambiguity could duplicate policy or hide lifecycle
state. It deliberately does not freeze internal fitness representation, collective
operation, or helper names that do not affect those boundaries.

## Semantic boundary

At one qualifying Lightning boundary, each member contributes one local fitness value.
Population resolution produces the complete stable-member-associated fitness population
needed to select one checkpoint source.

A successful result contains exactly one finite comparable fitness for every configured
member. Stable member identity must remain mechanically associated with the distributed
rank carrying its value.

Population resolution does not own the distributed context through which those values are
exchanged.

## Complete-Clan topology

`ClanScheduler` owns the configured Clan population and stable Tune-trial-to-member
assignment. `ClanScheduler.wrap(train)` makes that hidden assignment and the cohort
rendezvous available inside independently launched Tune function processes without
modifying the user's `genome` mapping.

The hidden runtime coordinator owns only stable member mapping and the rendezvous facts
needed for the complete function-invocation cohort. It does not select a winner, mutate
genomes, checkpoint training state, create a process group, or choose a backend.

The initial path requires the complete Clan to be concurrently resident before DDP
initialization. More sophisticated placement, gang admission, elastic membership, and
failure recovery require separate evidence and do not change the ownership above.

## Framework-managed distributed context

Lightning, PyTorch, and the external Tune process lifecycle own:

- process-group initialization and lifetime;
- backend and device behavior;
- rank and world-size realization from the supplied topology;
- training-gradient communication;
- barriers and collective execution; and
- distributed failure behavior and release through the qualified framework lifecycle.

For the initial DDP path, the already-established training world also carries the fitness
exchange. CBT production code does not construct, choose a backend for, or tear down a
second Ray, GLOO, NCCL, CUDA, or PyTorch process group.

`TuneMemberEnvironment` supplies externally assigned topology to Lightning.
`ClanDDPStrategy` retains ordinary Lightning/PyTorch DDP ownership and does not select a
backend unless the user explicitly supplies Lightning's normal `process_group_backend`
argument.

## Population exchange

`ClanTuneReportCallback` invokes the population exchange at the validation boundary. The
current implementation gathers one local scalar from each member through the active
PyTorch distributed world and returns the rank-ordered values to the framework-independent
worker decision.

That exchange owns only the communication needed to recover the complete fitness
population. It does not own:

- process-group lifecycle or backend choice;
- minimizing or maximizing policy;
- tie-breaking policy;
- genome mutation;
- Tune checkpoint/configuration transfer; or
- userspace genome application.

The exact scalar representation and collective primitive remain replaceable implementation
details as long as the complete identity-associated population is preserved.

## Framework-independent selection policy

The shared selection policy owns:

- comparison direction;
- comparison-validity rules;
- stable deterministic tie behavior; and
- selection of one stable member from a complete fitness population.

Workers and the Tune scheduler use the same implementation. The distributed exchange does
not contain another winner-selection policy.

## Worker controller

`ClanController` owns one ephemeral worker decision:

- stable local member identity;
- comparison mode;
- one local fitness value;
- one invocation of the supplied population exchange;
- application of the shared selection policy;
- the resolved selected-member identity; and
- one cached answer to whether the local member is the checkpoint source.

It does not know the genome, mutate configurations, write checkpoints, report to Tune,
construct distributed groups, or persist generation state.

Ordinary users do not need to construct `ClanController`; `ClanTuneReportCallback`
supplies the established DDP exchange internally. Direct construction remains useful for
framework-independent tests and advanced composition.

## Round reporting and checkpoint source

`ClanTuneReportCallback` owns the process-local boundary between Lightning and Tune. It:

1. reads the local Lightning fitness metric;
2. obtains the complete fitness population over the established DDP world;
3. resolves the selected member through `ClanController`;
4. asks every rank to enter Lightning's ordinary distributed checkpoint operation;
5. reports metrics from every member; and
6. reports a Ray checkpoint only from the selected member.

The callback never interprets or applies the Tune genome.

Every DDP rank must participate in `Trainer.save_checkpoint()` because Lightning's public
checkpoint operation includes a distributed barrier. `ClanDDPStrategy` gates only the
physical CBT round write: while that round checkpoint is active, only the selected rank
delegates to `CheckpointIO`. Losing ranks may construct transient checkpoint dictionaries
in memory but persist no CBT continuation.

Outside that scoped operation, ordinary user-requested Lightning checkpoint behavior is
unchanged.

## Producer provenance

The selected reported checkpoint carries producer metadata containing:

- schema version;
- stable member identity; and
- the exact scheduler-controlled genome values that produced the continuation.

`ClanTuneReportCallback` attaches this metadata to the selected Ray checkpoint before it
is reported. The metadata records provenance only; it is not another genome or evolution
authority.

The scheduler also receives a scalar JSON representation of the producer genome in the
ordinary Tune result because Tune flattens nested result mappings before scheduler hooks.
That private representation is an implementation detail and never changes the user's
`genome` argument.

## CBT Tune scheduler

`ClanScheduler` is the authoritative evolutionary owner and is implemented as a
synchronous Ray `PopulationBasedTraining` specialization. It:

- coordinates the configured live Clan and stable member assignment;
- waits for one report from each required trial at the synchronous PBT boundary;
- associates each result with the correct stable member and active controlled genome;
- independently applies the shared winner-selection policy;
- verifies worker agreement and the sole checkpoint source;
- clones the selected genome for target members;
- applies `MutationSpec` rules only to the declared controlled keys;
- owns the mutation random stream; and
- delegates checkpoint/configuration reassignment and function restart to Ray's native PBT
  machinery.

The winner retains the exact selected genome. Losing targets receive mutations of that
selected genome. The scheduler does not interpret the semantic meaning of any genome key.

Broader crash-consistent generation recovery and flexible cohort admission are not
qualified by the initial function path and must not be inferred from the scheduler's use
of native PBT persistence.

## User training code

User code owns the meaning and application of the genome.

On a resumed function invocation, Ray provides the selected checkpoint and the target
member's current genome. The user's function restores inherited state and explicitly
applies the new genome in whatever way its training system requires. CBT provides no
optimizer applier, no post-restore optimizer callback, and no inferred optimizer schema.

For Lightning's `ckpt_path` restore path, the public example applies the genome to the
restored optimizer state in a member-local checkpoint copy before `Trainer.fit()` performs
its final full-state restore. Other user systems may apply their genome differently.

## Failure ownership

Each layer fails the facts it owns:

- user code fails unsupported or invalid genome application;
- `ClanController` rejects invalid local decision lifecycle and non-finite fitness;
- population exchange fails if the established distributed operation cannot complete;
- Lightning/PyTorch and the Tune process lifecycle surface distributed setup,
  communication, and process failure;
- Lightning/`CheckpointIO` surface checkpoint construction or write failures; and
- `ClanScheduler` rejects incomplete or inconsistent reported population state.

No layer may convert a failure into a valid smaller-population winner.
