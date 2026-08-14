# Current integration design

Status: accepted design for the current implementation

## Purpose

This document defines the current system lifecycle, state authorities, and framework
boundaries. It does not repeat the Clan Tuning method, choose a distributed backend, or
replace the public usage documented in [`../api.md`](../api.md).

The implementation follows Ray Tune's ordinary function-trainable and PBT lifecycle as
far as possible. ClanBasedTuning adds only the coordination needed to make those Tune
members cooperate through one Lightning/PyTorch DDP world and to replace PBT's population
policy with the Clan single-parent transition.

## User-visible lifecycle

The public path begins with an ordinary Tune function:

```python
def train(genome):
    ...
```

The mapping passed by Tune is the member's current genome. ClanBasedTuning does not add
private topology fields to that mapping, infer what its keys mean, or apply those values
to an optimizer or another training object.

On the first invocation, the user's code constructs its training state from the initial
genome. On a resumed invocation, Ray supplies the selected parent checkpoint and the
member's newly assigned genome. The user's function restores the inherited state and
explicitly applies the current genome before training resumes.

For Lightning, the final full-state restore normally happens inside
`Trainer.fit(..., ckpt_path=...)`. A user may therefore update the optimizer state in a
member-local copy of the inherited checkpoint before passing that copy to Lightning, as
the public example does. That is userspace restore/application logic, not a CBT callback
or optimizer adapter.

## Tune population and scheduler

One live Tune trial represents one stable Clan member. The initial DDP path uses one
Lightning process and one distributed rank per trial.

`ClanScheduler` specializes Ray's synchronous `PopulationBasedTraining`. Ray continues to
own trial creation, resource requests, pause/resume behavior, checkpoint registration,
checkpoint reassignment, function restart, and trial configuration transfer. The CBT
scheduler replaces only the population policy and adds the cohort information required by
the cross-trial DDP path.

The configured mutation keys identify the subset of the Tune genome that the scheduler
evolves. They are not an optimizer schema. A key may have any meaning compatible with the
user's training function and with Clan Tuning's shared-gradient assumptions.

At a completed boundary, the scheduler independently verifies the complete population and
the selected member. Ray's native synchronous PBT machinery then assigns the selected
checkpoint to target members. The winner keeps its exact genome; each losing target
receives a copy of the winner genome with the declared `MutationSpec` rules applied.

## Hidden cohort context

Separate Tune function trials do not naturally know that they are members of one DDP
world. `ClanScheduler.wrap(train)` carries this missing context beside the user function
without changing `train(genome)` or inserting private values into `genome`.

A small named Ray coordinator owns only:

- stable Tune-trial-to-member assignment; and
- rendezvous facts for the complete function invocation cohort.

It does not select a winner, mutate genomes, checkpoint training state, choose a backend,
create a process group, or participate in training collectives.

The initial path requires the complete Clan to be concurrently resident. A member waits
for the complete registered cohort before DDP initialization. More sophisticated gang or
elastic admission remains an operational extension; partial participation is never
reinterpreted as a smaller valid Clan.

## Framework-managed distributed context

`TuneMemberEnvironment` exposes the externally assigned member rank, world size, and
rendezvous endpoint through Lightning's `ClusterEnvironment` seam.

`ClanDDPStrategy` remains an ordinary Lightning `DDPStrategy`. It supplies that environment
and the complete Clan sampler topology. Lightning/PyTorch still initialize and use the
process group.

Production CBT does not select GLOO, NCCL, CPU, CUDA, or another distributed backend. If
the user does not pass `process_group_backend`, Lightning/PyTorch make their normal backend
choice from the active device. A user may still pass the ordinary Lightning DDP backend
argument when deliberately selecting a supported backend.

The strategy disables DDP's per-forward buffer broadcast so member-local parameter and
buffer evolution is not silently overwritten after optimizer updates. It otherwise keeps
native DDP gradient communication and initial synchronization.

The qualified externally launched Lightning path may leave the process group initialized
after `Trainer.fit()` returns. ClanBasedTuning does not call
`torch.distributed.destroy_process_group()` to compensate. Group release follows the
qualified framework/external process lifecycle.

## Shared training and local fitness

During training, every member contributes its local batch work to native DDP gradient
reduction. Corresponding parameters therefore receive the same reduced gradient before
member-local optimizer behavior causes trajectories to diverge.

Training data may use Lightning's ordinary distributed sampler. Fitness evaluation must
remain member-local: the distinct candidate metric values cannot be reduced into one
shared Lightning metric before Clan selection.

At the qualifying validation boundary, `ClanTuneReportCallback` reads one local fitness
value from each member. It exchanges those scalar values through the already-established
PyTorch distributed world. It does not initialize another group or choose the active
backend.

Each worker uses the shared deterministic selection policy to identify the same selected
member before checkpoint reporting. The Tune scheduler later selects independently from
the reported population and rejects disagreement.

## One persistent continuation

The selected member is the sole persistent training continuation for a Clan round.
Population size must not multiply CBT checkpoint storage.

Lightning's public `Trainer.save_checkpoint()` is a distributed operation and requires all
ranks to participate. Therefore every Clan rank enters ordinary Lightning checkpoint
construction and its final barrier. Transient checkpoint dictionaries may exist in memory
on every rank at that boundary.

`ClanDDPStrategy` scopes only the physical write for the CBT round checkpoint: while the
round checkpoint is active, only the selected rank delegates the checkpoint to
Lightning's configured `CheckpointIO`. Losing ranks perform no persistent write. Outside
that scoped operation, ordinary user-requested Lightning checkpoint behavior is unchanged.

The selected rank reports the resulting Ray checkpoint together with producer provenance
containing its stable member identity and the exact scheduler-controlled genome values
that produced the state. Losing members report metrics but no Ray checkpoint.

## Generation transition

For each completed population boundary, the CBT Tune scheduler:

1. receives one report from every configured member;
2. verifies stable member identity and the active controlled genome values;
3. independently applies the deterministic selection policy;
4. verifies that all workers reported the same selected member and that only that member
   supplied the continuation;
5. uses Ray's native PBT checkpoint/configuration transfer to make the selected
   continuation the parent for the next target members; and
6. mutates the declared genome keys for losing targets while preserving the selected
   member's exact genome.

The resumed Tune function then receives the assigned checkpoint and genome. Userspace
code owns the restore/application step; the next Lightning run uses the resulting local
training state.

The current implementation relies on Ray's scheduler persistence for inherited native PBT
state and serializes the CBT scheduler's own mutation random stream as ordinary scheduler
object state. Broader crash-consistent generation recovery has not yet been qualified and
is not claimed by the initial path.

## Responsibility boundaries

- **User training code** owns genome interpretation and application, model construction,
  optimizer construction, and any application logic needed after restore.
- **Ray Tune** owns trial execution, resources, function lifecycle, native scheduler
  lifecycle, checkpoint registration/transfer, and configuration transfer.
- **`ClanScheduler`** owns stable Clan population assignment, authoritative population
  verification, deterministic winner authority, mutation rules and random state, and the
  next genome assigned to each target.
- **The hidden runtime coordinator** owns only stable member mapping and complete-cohort
  rendezvous facts for independent Tune function processes.
- **Lightning/PyTorch** own training execution, distributed initialization, backend/device
  behavior, model synchronization, gradient communication, collective execution, full
  checkpoint construction, restore semantics, and checkpoint barriers.
- **`ClanDDPStrategy` and `TuneMemberEnvironment`** adapt externally launched Tune members
  to those native Lightning/PyTorch responsibilities and gate only the selected CBT
  checkpoint write.
- **`ClanTuneReportCallback`** reads local fitness, performs the population fitness
  exchange over the established group, requests the distributed round checkpoint, and
  reports metrics plus the winner checkpoint to Tune. It never applies a genome.
- **Framework-independent policy code** owns deterministic winner comparison and scalar
  mutation behavior without framework lifecycle.
- **`ClanController`** owns one worker's local fitness, one cached population decision,
  and the resolved selected-member identity for that boundary.

There is no package-owned Trainer, Trainable lifecycle, optimizer applier, second training
loop, second process group, or backend-selection subsystem.

## Current qualification boundary

The real repeated contract currently exercises the public function path with two
concurrent Tune members on one machine using CPU Lightning training. The production path
is backend-neutral, but only the directly exercised device/backend combination is
qualified by that evidence.

The contract proves repeated function invocation, DDP participation, population fitness
exchange, winner agreement, Ray checkpoint/configuration handoff, explicit userspace
genome application after optimizer-state restore, and one physical Lightning checkpoint
write per Clan round.

Incomplete-cohort failure behavior, CUDA/NCCL execution, multi-node operation, broader
checkpoint stores, elastic membership, actor reuse, arbitrary optimizer layouts, and
model-sharded Clan execution require separate evidence before support is claimed.

## Later model-sharded execution

The initial supported topology uses one distributed training process per Clan member. A
later ClanFSDP extension may need a composed topology representing both model shards and
Clan members while retaining framework ownership of the resulting groups. Its mesh,
process layout, and FSDP hooks remain deliberately undesigned here.
