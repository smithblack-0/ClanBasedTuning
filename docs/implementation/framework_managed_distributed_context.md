# Initial framework-managed distributed context

Status: implemented foundation for the current function API  
Framework basis: Ray Tune, Lightning, and native PyTorch DDP

## Authority

This document records the distributed implementation choice underneath the current
[integration design](../design/integration.md). The complete generation behavior and
userspace API are defined elsewhere; this file explains only how independently launched
Tune members share one framework-owned DDP context.

## Implemented topology

The initial topology is:

```text
one live Ray Tune trial
    = one stable Clan member
    = one externally launched Lightning training process
    = one rank in the native PyTorch DDP group spanning the Clan
```

Ray Tune creates and resources trial processes. `ClanScheduler` assigns stable member
identity. The wrapped function runtime coordinates per-invocation rendezvous and provides
rank/world-size/address/port facts to `ClanDDPStrategy` through `TuneMemberEnvironment`.
Lightning and PyTorch then initialize and use the DDP group.

CBT does not create a separate population process group.

## Cohort assignment and rendezvous

The scheduler collects the complete configured set of Tune trial IDs and assigns stable
member IDs by a deterministic ordering. In the initial topology, stable member ID is also
the member's DDP global rank.

The hidden worker runtime waits until its Tune trial has a registered member assignment.
For each function invocation:

- every member announces a fresh invocation token and host;
- rank/member zero contributes a free rendezvous port;
- the coordinator opens the session only after every assigned member has announced; and
- each member receives the same rendezvous address/port together with its own stable rank.

The runtime has a bounded pre-DDP join timeout. It does not own the PyTorch process group
or attempt to recover a group after initialization.

The complete population must fit concurrently in available Ray resources. The initial
implementation does not provide a separate gang-reservation layer that can guarantee no
partial set of trials temporarily occupies cluster capacity while waiting for the rest.
That is a known hardening/support limitation, not an invitation to time-multiplex members
inside one Clan DDP round.

## Lightning topology seam

`TuneMemberEnvironment` is an internal Lightning `ClusterEnvironment`. It reports the
externally assigned:

- global rank;
- world size;
- local rank;
- logical node rank; and
- rendezvous address and port.

It declares that the processes were created externally. It does not import Ray, choose a
backend, initialize or destroy a process group, perform collectives, or manage CUDA.

`ClanDDPStrategy` supplies that environment to Lightning's ordinary `DDPStrategy`. The
initial path requires exactly one Lightning process/device per Tune trial.

## Framework ownership

Lightning, PyTorch, and the external Tune trial process lifecycle own:

- accelerator and process-group backend selection;
- process-group initialization;
- DDP model setup;
- gradient reduction and DDP synchronization;
- barriers and collectives;
- device behavior; and
- distributed process-group lifetime within the qualified external-launch path.

Direct evidence with Ray 2.56.1, Lightning 2.6.5, and PyTorch 2.10.0 shows that Lightning
leaves the DDP group initialized when `Trainer.fit()` returns in this externally launched
topology. The Tune function process then exits, releasing that framework-owned context.
CBT does not add package-owned teardown to compensate.

Consequently, actor/process reuse across Clan generations is not currently supported by
the complete function path.

## Shared training behavior

The retained two-member CPU contract gives the ranks distinct local gradients and verifies
that Lightning/PyTorch reduce them to one common gradient before the local optimizer
updates.

`ClanDDPStrategy` disables DDP's per-forward buffer broadcast so persistent member-local
buffer changes are not copied from one rank onto the others after setup. Gradient
communication remains ordinary DDP.

Training data follows Lightning's ordinary distributed-sampler behavior unless user code
configures another supported loader arrangement.

## Population resolution on the same context

At the qualifying validation boundary, `ClanTuneReportCallback` contributes one local
fitness tensor per member through `trainer.strategy.all_gather()`.

Because stable member ID equals global rank in this initial topology, gathered rank order
has an explicitly established stable-member meaning. `ClanController` then applies the
shared framework-independent winner policy to that complete vector.

The population operation therefore uses the same Lightning/PyTorch-managed context as
training. There is no package-owned Ray collective group, second rendezvous, or CBT backend
choice for population selection.

## Checkpoint barrier on the same context

Lightning's `Trainer.save_checkpoint()` constructs checkpoint state, calls the strategy
save hook, and then executes a strategy barrier.

For a CBT round, `ClanDDPStrategy` temporarily records the selected source rank. Every
member enters the normal Lightning checkpoint call; only that rank delegates the
checkpoint file to `CheckpointIO`. The Trainer barrier remains unchanged.

This is why transient checkpoint construction on every member is compatible with the
one-persistent-continuation storage contract.

## Userspace boundary

The hidden distributed runtime does not store the Tune genome and does not inspect the
function's config dictionary. `ClanScheduler.wrap(train)` establishes the runtime context
and then calls the user function with Ray's original config argument.

Genome interpretation and application remain entirely in user code. The distributed
integration does not introduce an optimizer application abstraction merely because the
Clan method commonly varies optimizer hyperparameters.

## Current support limits

This implementation foundation is directly qualified only for the initial two-member,
single-node CPU path. It does not establish:

- CUDA/NCCL;
- multi-node rendezvous;
- actor reuse;
- bounded recovery after a member disappears inside an active framework collective;
- automatic identical validation-set replication;
- arbitrary Lightning strategies or third-party distributed backends; or
- model-sharded ClanFSDP execution.

The complete repeated-generation evidence and its additional limits are recorded in
[`../qualification/function_api.md`](../qualification/function_api.md).

## Superseded direction

The former package-owned Ray collective group for population resolution is rejected. It
would duplicate a distributed context already required for shared training and transfer
backend/rendezvous lifecycle into CBT without a Clan-specific need.

Likewise, the former controller-centric `make_cbt_controller(genome=...)` / checkpoint
`save_genome()` public direction is superseded by the ordinary Tune function API. The
worker runtime carries hidden topology; the user function receives and owns the genome.
