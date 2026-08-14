# Initial framework-managed distributed context

Status: implementation record for the current function API

## Topology

The initial topology is:

```text
one live Ray Tune trial
    = one stable Clan member
    = one externally launched Lightning process/device
    = one rank in the PyTorch DDP group spanning the Clan
```

Ray creates/resources trial processes. `ClanScheduler` assigns the stable member mapping and
registers it in a small internal Ray registry/coordinator. `ClanDDPStrategy`, constructed in
the ordinary Tune function, discovers the current trial's assignment and supplies the
resulting rank/world-size/address/port to Lightning through `TuneMemberEnvironment`.

There is no CBT function wrapper and no CBT-owned distributed process group.

## Cohort assignment and rendezvous

After the complete Tune trial set is known, the scheduler assigns member IDs by deterministic
trial-ID ordering and registers the same runtime spec for every trial. For each function
invocation every member announces a fresh token and host; member zero contributes the
rendezvous port; the coordinator opens a session only after the full assigned cohort has
announced.

The pre-DDP join has a bounded timeout. The current implementation does not yet provide a
separate gang reservation layer or recovery for a participant disappearing inside an active
PyTorch collective.

For interrupted Tune experiments, scheduler state retains the coordinator identity, member
mapping, and runtime spec while live Ray actor handles are intentionally excluded from
serialization. When the experiment is restored, scheduler hooks re-establish the registry
and coordinator before Ray resumes the member trials.

## Lightning ownership

`TuneMemberEnvironment` reports externally assigned topology; it does not import Ray,
choose a backend, initialize/destroy a process group, or manage CUDA. `ClanDDPStrategy`
passes it to Lightning's ordinary `DDPStrategy`.

Lightning/PyTorch own backend/device selection, process-group creation, DDP model setup,
gradient reduction, barriers, and process-group lifetime. The current strategy requires one
local process/device per Tune member. Ray's resource annotation is the ordinary place to
assign that device; explicit `Trainer(devices=1)` is unnecessary in the public path.

## Training and validation data

Training keeps Lightning's ordinary DDP partitioning. For Lightning-managed validation and
sanity validation, the strategy supplies sampler kwargs equivalent to one replica on every
member so each candidate evaluates the same complete held-out set. Explicit user-provided
`DistributedSampler` objects remain untouched and are outside the current automatic-sampler
support claim.

## Population exchange and checkpointing

At validation end, `ClanTuneReportCallback` gathers one scalar fitness per member through
`trainer.strategy.all_gather()` on the same framework-owned group used for training.

Every rank enters `Trainer.save_checkpoint()` at a Clan boundary so Lightning's checkpoint
construction and post-save barrier remain intact. Only the selected rank delegates the
scoped round checkpoint to `CheckpointIO`; only that member reports the Ray checkpoint.

## Userspace boundary

The runtime never stores/interprets the Tune config. A receiving function gets the current
config as its normal function argument and the selected continuation from
`tune.get_checkpoint()`. Applying changed optimizer policy is explicit user code.

The internal topology registry exists only because independent Tune trials need shared
rendezvous facts; it is not an application or optimizer abstraction.

## Current support limits

Direct complete-path support is still limited to the qualification envelope in
[`../qualification/function_api.md`](../qualification/function_api.md). CUDA/NCCL,
multi-node, actor reuse, active-collective failure recovery, custom/sharded checkpoint
plugins, explicit distributed validation samplers, and model-sharded Clan execution remain
separate qualification work.
