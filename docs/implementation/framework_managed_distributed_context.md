# Framework-managed distributed context

Status: implementation record for the current DDP topology

## Topology

The initial path maps one live Ray Tune trial to one stable Clan member, one externally
launched Lightning process/device, and one PyTorch DDP global rank. Ray creates/resources the
trial process; CBT supplies the missing Clan topology; Lightning/PyTorch create and own the
actual distributed group.

Every Tune trial sees one process-local device, so the Lightning environment reports local
rank zero. To preserve the externally assigned global member rank through Lightning's normal
launcher-oriented rank model, each Tune member is represented as one logical one-process
node: logical node rank equals member/global rank. This is not a statement about physical
machine placement.

## Runtime handoff

After Tune has created the complete configured trial set, `ClanScheduler` deterministically
assigns stable member IDs from sorted trial IDs. It registers an experiment-scoped runtime
specification in a named registry actor and the complete trial/member mapping in a named
coordinator actor.

Inside the ordinary Tune function, `ClanDDPStrategy` calls `join_runtime()`. Tune context
provides experiment/trial identity; the runtime adapter retrieves the scheduler assignment,
announces a fresh invocation token/host, and waits for the complete cohort. Member zero
provides the rendezvous port used by Lightning/PyTorch.

Pure member/session rules live in `cohort.py`; Ray actor, context, socket, and timeout effects
live in `runtime.py`.

## Framework ownership

`TuneMemberEnvironment` is a Lightning `ClusterEnvironment`. It reports immutable external
rank/world-size/rendezvous facts and declares that processes were launched externally. It
does not import Ray, choose a backend, initialize/destroy a process group, or perform a
collective.

`ClanDDPStrategy` subclasses Lightning's normal `DDPStrategy`. Lightning/PyTorch retain
backend/device selection, process-group initialization, model wrapping, gradient all-reduce,
barriers, and framework cleanup. CBT creates no additional distributed group.

Direct framework evidence previously established two Tune CPU processes forming one GLOO DDP
world and receiving the same reduced gradient. The corrective scheduler refactor does not
change this topology seam, but exact-branch framework tests remain the authority for current
support.

## Data behavior

Training uses Lightning's ordinary DDP partitioning. Candidate fitness must compare equivalent
held-out workloads, so during Lightning-managed validation/sanity validation the strategy
reports sampler kwargs for one replica/rank zero on every member. Each candidate therefore
sees the complete validation dataset.

Explicit user-supplied distributed samplers remain user-owned and are not automatically
rewritten by CBT.

## Checkpoint boundary

Every rank enters `Trainer.save_checkpoint()` because Lightning checkpointing retains its
collective/barrier behavior. During one scoped Clan round checkpoint,
`ClanDDPStrategy.save_checkpoint()` delegates to `CheckpointIO` only on the selected global
rank. Losing ranks participate in framework construction/barrier but persist no Clan round
file.

The selected Tune checkpoint is then transferred driver-side by `ClanScheduler` through the
narrow Ray compatibility adapter.

## Failure and support boundary

The scheduler waits until Tune has created the full configured population before launching
members. Runtime rendezvous has a bounded timeout before DDP initialization. This does not
atomically reserve resources for multiple independent Tune trials; the current support model
requires the entire Clan to fit concurrently on provisioned capacity.

The project does not yet claim bounded recovery after a process disappears inside an active
PyTorch collective, CUDA/NCCL, physical multi-node topology, arbitrary validation samplers,
or model-sharded Clan execution. Those require direct evidence rather than inference from the
single-node CPU seam.
