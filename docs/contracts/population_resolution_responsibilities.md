# Population-resolution responsibilities

Status: accepted and implemented for the initial DDP path

## Purpose

This document assigns ownership for the population boundary defined by
[`population_resolution_invariants.md`](population_resolution_invariants.md). It fixes
semantic authority without turning transport details into public API.

## Complete-Clan topology

`ClanScheduler` owns the configured Clan population and assigns stable member identity to
Tune trial identity. It registers that assignment in the internal runtime registry and
cohort coordinator before members run. The ordinary user trainable remains unwrapped.

For the initial path, stable member ID is deliberately the corresponding DDP global rank.
The complete population must be concurrently resident; an incomplete population is never
reinterpreted as a smaller valid Clan.

## Framework-managed distributed context

Lightning/PyTorch own process-group initialization/lifetime, backend and device behavior,
rank/world-size realization, DDP gradient communication, barriers, and collective execution.
The same already-established group carries population fitness. CBT creates no second Ray,
GLOO, NCCL, CUDA, or PyTorch collective group for selection.

## Fitness exchange and selection

`ClanTuneReportCallback` exchanges one local fitness per member through
`trainer.strategy.all_gather()`. `ClanController` verifies the complete finite vector and
applies the shared deterministic selection rule. The Tune scheduler independently applies
the same rule to the complete trial results and rejects disagreement.

Metric direction belongs to Ray's ordinary scheduler configuration. Users configure
`metric` and `mode` on `TuneConfig`; the scheduler receives those through Ray and registers
the same contract for the member-side runtime.

## Worker runtime

The internal runtime registry/coordinator owns only facts needed to connect separate Tune
trials into one externally launched Lightning DDP world:

- trial-to-stable-member assignment;
- population size;
- comparison metric/mode;
- rendezvous address/port; and
- per-invocation cohort synchronization.

It has no genome field and does not inspect the Tune config. `ClanDDPStrategy` discovers the
runtime for the current Tune trial directly; there is no public CBT trainable wrapper.

The scheduler's serializable state retains the runtime identity/member assignment but not
live actor handles. On Tune experiment restore, scheduler hooks re-create/register those
actors before resumed trials run.

## `ClanTuneReportCallback`

The callback bridges a qualifying Lightning validation boundary to Tune:

1. read one member-local Lightning fitness;
2. exchange the complete fitness vector over the active Lightning strategy;
3. resolve one common winner;
4. have every rank participate in Lightning checkpoint construction/barrier while only the
   winner persists the Clan continuation; and
5. report ordinary metrics from every trial and a Ray checkpoint from the winner only.

The callback has no genome-application responsibility.

## `ClanScheduler`

`ClanScheduler` is a synchronous Ray `PopulationBasedTraining` specialization. It owns:

- stable Clan membership and runtime registration;
- verification of one complete generation boundary;
- independent winner selection and worker/scheduler agreement;
- verification of the single checkpoint source;
- snapshotting the selected parent's Tune config;
- one independent mutation for every next member, including the prior winner; and
- the mutation random stream.

Ray owns actual pause/checkpoint/config/restart and experiment restoration. CBT does not
create another trial lifecycle.

## Lightning strategy and checkpoint ownership

Every rank participates in the Clan round checkpoint call because Lightning's
`Trainer.save_checkpoint()` is collective. `ClanDDPStrategy` changes only which selected
rank delegates that scoped checkpoint to `CheckpointIO`; the Trainer barrier remains
framework-owned.

Ray owns per-trial resources. The current topology allows one local Lightning process/device
per Tune trial; the strategy rejects more. Ordinary users therefore configure the device
once through Ray resources rather than repeating `devices=1` in the Trainer.

## User code

User code owns every interpretation and application of the Tune config/genome. Neither
population resolution nor any other CBT component may infer optimizer mappings or arrange
application for the user. Scientifically valid Clan variation must be applied after the
shared gradient is computed.

## Failure ownership

Each layer rejects facts it can establish. The runtime times out if the assigned cohort does
not rendezvous before DDP initialization; the scheduler rejects malformed/incomplete Tune
boundaries; Lightning/PyTorch surface distributed and checkpoint failures. No layer may
convert a known failure into a valid partial-population winner.

Bounded recovery after a participant disappears inside an active framework collective is
not yet a qualified support claim.
