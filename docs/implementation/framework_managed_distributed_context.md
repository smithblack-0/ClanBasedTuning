# Initial framework-managed distributed context

Status: current implementation choice  
Framework basis: Ray Tune, Lightning, and native PyTorch DDP

## Authority

This document records the replaceable mechanisms currently used to satisfy the
[integration design](../design/integration.md) and the
[population-resolution responsibilities](../contracts/population_resolution_responsibilities.md).

The public behavior and ownership contracts are authoritative over these details.

## Implemented topology

The initial path uses:

```text
one live Ray Tune trial
    = one stable Clan member
    = one externally launched Lightning training process
    = one rank in the native PyTorch DDP world spanning the Clan
```

`ClanScheduler.wrap(train)` carries a private `ClanRuntimeSpec` beside the serialized
function. Inside each Tune process, the wrapper joins a named Ray coordinator and installs
a process-local runtime context before calling the user's unchanged `train(genome)`.

The user genome contains only Tune configuration. Member identity, rank, world size, and
rendezvous facts are not inserted into it.

## Stable member assignment and rendezvous

`ClanScheduler` collects the configured Tune trial IDs. Once the complete population is
known, sorted trial IDs receive stable integer member IDs `0..population_size-1`.

A named Ray coordinator retains that assignment and forms one rendezvous session from one
fresh invocation token per member. Member zero contributes the rendezvous host/port; each
member receives its stable member/rank and the common endpoint.

The coordinator owns no training or evolution state. It does not:

- create a PyTorch process group;
- select a distributed backend;
- exchange gradients or fitness;
- select the winner;
- mutate genomes; or
- persist checkpoints.

The current path assumes Tune can run the complete population concurrently. If the full
cohort does not arrive before the configured timeout, the invocation fails rather than
shrinking the Clan. Native gang placement for insufficient cluster capacity is not yet
implemented or qualified.

## Lightning topology seam

The process-local runtime feeds `TuneMemberEnvironment`, a Lightning
`ClusterEnvironment` reporting:

- externally assigned global rank;
- complete world size;
- local and logical node rank; and
- rendezvous address and port.

`ClanDDPStrategy` constructs that environment and otherwise remains a Lightning
`DDPStrategy`.

Lightning's standard `DDPStrategy.set_world_ranks()` assumes world size can be reconstructed
from Lightning's own `num_nodes * num_processes`. That is not true for one process inside
each independent Tune trial, so `ClanDDPStrategy` preserves the externally assigned rank
and world size instead.

The strategy also exposes the complete Clan rank/world to Lightning's distributed sampler
and sets `broadcast_buffers=False` so per-forward buffer synchronization cannot erase
member-local divergence.

## Backend ownership

Production CBT passes no default process-group backend.

When the user does not provide Lightning's normal `process_group_backend` argument,
`DDPStrategy` chooses the backend from its root device. When a user explicitly provides
that ordinary argument, CBT passes it through.

The implementation contains no production GLOO/NCCL selection and does not call
`torch.distributed.init_process_group()` or `torch.distributed.destroy_process_group()`.

The earlier topology contract explicitly requests GLOO only to qualify a deterministic CPU
test. The repeated function-API contract leaves backend choice to Lightning/PyTorch.

## Population fitness exchange

At validation end, `ClanTuneReportCallback` reads one local scalar fitness from each
member. It constructs an ephemeral `ClanController` whose exchange function uses
`torch.distributed.all_gather` on the already-established default PyTorch distributed
world.

The local scalar tensor is created on `trainer.strategy.root_device`. The exchange
therefore follows the active DDP device/backend rather than creating a CPU-only side
channel.

The rank order is the stable member order for the initial topology, so the complete
fitness sequence can be passed directly to the shared deterministic selector. The Tune
scheduler independently repeats the same selection from reported results.

## Winner-only persistent checkpoint

Lightning's public `Trainer.save_checkpoint()` performs three relevant operations on every
rank:

```text
construct checkpoint dictionary
→ strategy.save_checkpoint(...)
→ strategy barrier
```

The callback therefore asks every member to enter that same operation after winner
selection. `ClanDDPStrategy` temporarily records the selected source rank for this CBT
round checkpoint.

During that scope:

- the selected rank delegates to the configured `CheckpointIO.save_checkpoint()`;
- losing ranks skip the physical write; and
- every rank still reaches Lightning's ordinary checkpoint barrier.

The callback then creates and reports a Ray `Checkpoint` only on the selected member.

This avoids the former private Lightning checkpoint-dump/barrier-bypass seam and preserves
the storage invariant of one persistent CBT continuation per round.

Outside this scoped operation, `ClanDDPStrategy.save_checkpoint()` delegates to ordinary
Lightning behavior so user-requested checkpoints are not globally winner-gated.

## Function restart and userspace genome application

`ClanScheduler` subclasses synchronous Ray `PopulationBasedTraining`. Its custom policy
marks every loser as a PBT target and the sole Clan winner as the source. The overridden
config transition clones the winner's Tune config and applies `MutationSpec` rules only to
the declared controlled keys.

Ray remains responsible for assigning the selected reported checkpoint, replacing target
configs, pausing/restarting function trials, and exposing the assigned checkpoint through
`tune.get_checkpoint()`.

The resumed user's function owns application. For the documented Lightning path it:

1. materializes the selected Ray checkpoint locally;
2. loads inherited optimizer state;
3. explicitly applies the current Tune genome to that optimizer;
4. writes the updated optimizer state into the member-local checkpoint copy; and
5. passes that copy to `Trainer.fit(..., ckpt_path=...)` for Lightning's complete restore.

No CBT callback or strategy applies genome values.

## Framework lifecycle

The qualified externally launched Lightning path leaves the PyTorch process group active
when `Trainer.fit()` returns. CBT does not insert explicit teardown. In the tested Tune
function lifecycle, the relevant worker/process lifecycle permits the repeated Clan path
to form the next distributed invocation successfully.

Actor reuse is not enabled or claimed. A future reuse path must directly qualify process
group teardown/reformation rather than assuming the current process lifetime behavior.

## Current evidence

The retained contracts establish:

- two real Tune trials forming one Lightning/PyTorch DDP world;
- common reduced gradients;
- two repeated Clan report boundaries through the function API;
- fitness exchange over the established DDP world;
- worker/scheduler winner agreement;
- native PBT checkpoint/configuration handoff;
- explicit userspace application of the resumed genome; and
- exactly one instrumented `CheckpointIO` persistence call per Clan round.

Exact versions and non-claims are recorded in
[`../qualification/function_api_workflow.md`](../qualification/function_api_workflow.md).

## Deferred implementation

The current mechanism does not implement or claim:

- gang admission when the cluster cannot concurrently schedule the complete Clan;
- elastic membership;
- actor reuse;
- comprehensive distributed failure recovery;
- multi-node topology;
- accelerator/backend combinations not directly qualified; or
- the later ClanFSDP topology.

The former package-owned Ray population collective remains rejected. Later model-sharded
work may require additional framework-owned process groups, but that is a separate design
and qualification problem rather than a reason to introduce a second communication system
into the initial DDP path.
