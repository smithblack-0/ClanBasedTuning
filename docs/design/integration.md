# Current integration design

Status: corrective implementation design

## Purpose

This document records component responsibilities and lifecycle ordering for the Ray Tune
function path. Public usage belongs in [`../api.md`](../api.md); executable evidence belongs in
qualification records.

## Runtime model

One live Ray Tune function trial is one stable Clan member, one externally launched
Lightning process/device, and one DDP global rank. Ray owns trial creation/resources and
function execution. The complete configured population must be concurrently runnable.

`ClanScheduler` uses Tune's scheduler lifecycle but owns the small synchronous Clan transition
rather than subclassing `PopulationBasedTraining`. This freezes Clan algorithm semantics
against Ray PBT refactors without replacing Tune's resource, storage, pause/resume, or
experiment-restoration systems.

Before members run, the scheduler assigns stable member IDs from the complete Tune trial set
and registers an experiment-scoped `ClanRuntimeSpec` in named Ray registry/coordinator actors.
The user's function remains ordinary and unwrapped. `ClanDDPStrategy()` discovers the current
trial's runtime from Tune context and receives member/rank/world-size/rendezvous facts.

## Framework-independent policy

`evolution.py` owns comparison, mutation-rule normalization, and complete next-generation
construction. Its input is member-ordered fitness/config data and a scheduler-owned random
stream. Its output is one selected parent and one child config per stable member.

Every child is independently mutated from one deep-copied parent config in stable member-ID
order. Framework iteration order cannot change seeded sibling assignment.

There is no persistent or worker-side `ClanController`. The Lightning callback gathers one
complete fitness vector and applies the same pure selection function the scheduler uses.

## Ray compatibility boundary

Tune's scheduler interface does not expose one stable public atomic operation for "resume
this trial from that trial's checkpoint and config." Ray PBT implements that operation with
Developer/private Tune state.

CBT therefore isolates three operations in `ray_compat.py`: capture the selected boundary
checkpoint, pause a trial without creating another checkpoint, and assign a config plus
inherited checkpoint to the paused trial. The scheduler contains no references to Ray PBT's
private class state or mutation helpers.

The dependency strategy is intentionally not an exact/minor Ray pin. Ray versions are
qualified empirically; if a future version changes those low-level operations, the
compatibility module is repaired and the real framework contracts rerun. Major-version
bounds remain appropriate because Ray provides no DeveloperAPI compatibility guarantee
across arbitrary releases.

## Userspace genome application

The current child config reaches the user function as its ordinary Tune argument. The
selected training continuation arrives independently through `tune.get_checkpoint()`.

Lightning restores model, optimizer, loop progress, and other checkpoint state before the
training stage invokes `LightningModule.on_train_start()`. The primary documented userspace
pattern therefore stores the current genome on the user's module and explicitly edits the
restored optimizer in `on_train_start`. CBT provides no application function, mapping schema,
restore callback, or optimizer inspection.

## Distributed topology

`TuneMemberEnvironment` presents each independently launched Tune process as one logical
one-process Lightning node. Local rank is zero; logical node rank and global rank identify the
stable member. This representation works with Lightning's launcher-oriented rank model while
Ray independently launches one visible device per member. It is not physical-node identity.

`ClanDDPStrategy` supplies that environment and prevents Lightning from spawning another
process. Lightning/PyTorch retain accelerator/backend choice, process-group creation, model
wrapping, gradient reduction, barriers, and teardown. CBT creates no second population
process group.

Per-forward DDP buffer broadcast is disabled after setup so one member's diverged persistent
buffers are not overwritten by rank zero. Training remains ordinarily partitioned; only
Lightning-managed validation sampler kwargs are changed to evaluate the full held-out set on
each candidate.

## Population and checkpoint boundary

At qualifying validation end:

1. each callback reads one member-local fitness;
2. the active Lightning strategy all-gathers one scalar per member;
3. every worker selects the same winner through `select_winner_id`;
4. every rank enters `Trainer.save_checkpoint()` so Lightning's construction/barrier remains
   intact;
5. `ClanDDPStrategy` lets only the selected rank delegate that scoped write to `CheckpointIO`;
6. every trial reports its metrics while only the winner reports a Ray checkpoint; and
7. the scheduler independently verifies complete membership, boundary, winner, and checkpoint
   source before constructing the next generation.

## Failure and restoration

The scheduler does not launch a member until Tune has created the complete configured trial
set. Runtime rendezvous then has a bounded timeout before DDP initialization. This does not
reserve cross-trial resources atomically; production use currently requires pre-provisioned
capacity sufficient for the entire Clan.

A known incomplete population is never converted into a smaller valid Clan. Failure inside an
active PyTorch collective is currently delegated to the framework/process lifecycle and must
be qualified before bounded recovery is claimed.

Scheduler serialization preserves algorithm/runtime identity and strips live actor handles.
Ray experiment restore recreates/registers those actors before members resume. There is no
CBT-specific restore API.

## Responsibility summary

- **Ray Tune:** trial execution/resources, scheduler callback invocation, storage,
  pause/resume, experiment persistence/restore.
- **ClanScheduler:** stable population identity, complete boundary verification, parent
  authority, sibling mutation, next-generation transition.
- **`ray_compat.py`:** minimal low-level Tune checkpoint/config transfer mechanics only.
- **Pure evolution:** selection, mutation, stable deterministic child generation.
- **Pure cohort state:** experiment/trial assignment and complete invocation sessions.
- **Ray runtime adapter:** named actors, Tune context discovery, timeout/socket effects.
- **Lightning/PyTorch:** device/backend/process group, DDP, gradients, loops, full-state
  restoration, checkpoint construction/barriers.
- **ClanDDPStrategy:** external topology, validation sampler distinction, selected-rank
  checkpoint persistence.
- **ClanTuneReportCallback:** local fitness exchange and Tune reporting boundary.
- **User code:** genome meaning/application and custom data/sampler behavior.
