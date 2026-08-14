# Current integration design

Status: implemented design for the Ray Tune function path

## Purpose

This document records the system lifecycle, authority boundaries, and the small framework
seams required for Clan Tuning. User-facing setup belongs in [`../api.md`](../api.md).

## Runtime model

One live Ray Tune function trial is one stable Clan member, one externally launched
Lightning process/device, and one rank in the DDP world spanning the Clan.

`ClanScheduler` is the Tune-side evolutionary authority. It specializes Ray's synchronous
Population Based Training lifecycle so Ray retains trial execution, scheduling/resources,
pausing, checkpoint transfer, restoration, and config replacement.

There is no CBT trainable wrapper. Before members run, the scheduler registers the complete
trial set and a `ClanRuntimeSpec` in an internal named Ray registry and cohort coordinator.
`ClanDDPStrategy`, constructed inside the ordinary user function, looks up the current Tune
trial ID in that registry and receives stable member/rank/world-size/rendezvous facts. The
user's config dictionary is never placed in that runtime and reaches the function unchanged.

The scheduler actor handles themselves are not serialized. Persistent scheduler state keeps
the coordinator identity, member assignment, mutation random stream, and runtime spec; when
Ray restores the Tune experiment, scheduler hooks recreate/register the named runtime actors
before resumed members are launched. This makes experiment recovery use Ray's ordinary
`Tuner.restore(..., trainable=...)` path instead of a CBT-specific restart API.

The complete population must be resident concurrently. The runtime waits for the assigned
cohort and fails its pre-DDP rendezvous after the configured timeout rather than silently
forming a smaller Clan.

## Configuration authority

Ray Tune owns the ordinary scheduler metric/mode and trial/resource configuration.
`ClanScheduler` receives `metric` and `mode` through the scheduler interface from
`TuneConfig`; users do not repeat them in a CBT constructor. Ray's resource annotation also
owns the one device allocated to each trial. Lightning's normal automatic device selection
is therefore the ordinary path; `ClanDDPStrategy` enforces the current invariant that each
member resolves exactly one local Lightning process/device.

Mutation rules are plain user dictionaries, validated once into a private internal form.
CBT needs the mutation behavior but does not need a public mutation-object hierarchy.

## Genome ownership and scientific boundary

CBT selects and mutates Tune config values but does not define what they mean. There is no
optimizer schema, inferred config-to-state mapping, application callback, restore hook, or
post-load application hook in production CBT. User code decides and visibly performs every
application.

That generic software boundary does not make every varying choice scientifically valid.
Clan members pool a common gradient, so valid variation must be applied after that gradient
is computed—normally optimizer-side policy such as learning rate, weight decay, momentum,
or betas. Model/data/forward/loss variation would change the training problem whose
gradients are pooled and is outside Clan Tuning.

## Distributed training lifecycle

`ClanDDPStrategy` supplies only topology facts that Lightning cannot infer across separate
Tune trials. Lightning and PyTorch retain accelerator/backend choice, process-group
initialization, DDP model setup, gradient collectives, barriers, training/validation loops,
and process-group lifetime.

CBT creates no second distributed group. It disables DDP per-forward buffer broadcast so
later member-local persistent buffers cannot be silently overwritten by another candidate.

Training keeps ordinary Lightning DDP partitioning. For Lightning-managed validation and
sanity validation, the strategy supplies one-replica sampler kwargs on every member so each
candidate sees the same complete held-out dataset. Explicit user `DistributedSampler`
objects remain user-owned and are not replaced.

## Population boundary

At validation end, `ClanTuneReportCallback` reads one member-local Lightning metric and
passes it to the framework-independent `ClanController`. Fitness exchange uses
`trainer.strategy.all_gather()` over the existing Lightning/PyTorch group. Every worker
applies the same deterministic winner rule locally. The scheduler independently verifies
the complete Tune results, same winner, and exactly one declared checkpoint source.

The candidate fitness must not be reduced across the Clan before this exchange.

## Selected continuation

Every rank enters ordinary `Trainer.save_checkpoint()` because Lightning's checkpoint
boundary includes a barrier. For the scoped Clan round, `ClanDDPStrategy` delegates the file
write only on the selected rank. Only that member turns the temporary checkpoint directory
into a Ray checkpoint and reports it; no losing continuation is persisted as a CBT round
checkpoint.

Ray's synchronous PBT machinery then transfers the selected checkpoint/config. The
scheduler snapshots the selected parent config and independently mutates that same snapshot
for every next member, including the prior winner. Child mutations are siblings, never a
chain through already-mutated children.

For a receiving user function, `tune.get_checkpoint()` supplies the selected Lightning
continuation while the function argument supplies the current child config. If the user
changes optimizer hyperparameters, userspace may load the inherited optimizer state, edit
it explicitly, write it into a local checkpoint copy, and pass that copy to
`trainer.fit(..., ckpt_path=...)` for normal full-state restoration.

## Responsibility summary

- **Ray Tune:** trial/resource/scheduler lifecycle, pause/restart, checkpoint/config transfer,
  experiment persistence and restore.
- **ClanScheduler:** complete stable membership, runtime registration, one-parent selection
  verification, mutation, next-config assignment.
- **Internal runtime registry/coordinator:** trial-to-member identity and per-invocation DDP
  rendezvous facts only.
- **Lightning/PyTorch:** device/backend/process group, DDP, gradients, loops, full-state
  restore, checkpoint construction/barrier.
- **ClanDDPStrategy:** Clan topology, training/validation sampler distinction, scoped
  selected-rank checkpoint persistence.
- **ClanTuneReportCallback:** one validation boundary to one Tune report/checkpoint boundary.
- **ClanController:** one local finite fitness and one complete-population selected-member
  decision.
- **User code:** genome meaning/application and explicit custom data/sampler behavior.

## Support boundary

The complete path is directly qualified only where the qualification record says so.
CUDA/NCCL, multi-node, actor reuse, active-collective failure recovery, custom/sharded
checkpoint plugins, explicit distributed validation samplers, and ClanFSDP remain separate
qualification work.
