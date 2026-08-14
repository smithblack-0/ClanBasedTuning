# Function-API Clan workflow qualification

Status: current direct evidence

## Scope

This record states what the real repeated function-API contract demonstrates. It does not
broaden the qualification requirements in
[`framework_managed_distributed_context.md`](framework_managed_distributed_context.md).
Unsupported adjacent configurations remain non-claims.

## Tested environment

The Ray-native contract runs with:

- Python 3.11;
- Ray Tune 2.56.1;
- Lightning 2.6.5;
- PyTorch 2.10.0;
- one machine;
- two concurrently resident Tune function trials;
- one CPU Lightning process/device per trial; and
- two Clan report boundaries.

The function-path production code does not pass `process_group_backend`. Lightning and
PyTorch therefore make their ordinary backend choice for the CPU devices. A separate
lower-level topology contract explicitly exercises CPU/GLOO, but that test backend is not
selected by production CBT code.

## Public path exercised

The contract uses the same integration shape documented for users:

```text
ClanScheduler.wrap(train)
→ Tune calls train(genome)
→ ClanDDPStrategy joins the complete cross-trial DDP world
→ Lightning trains and validates
→ ClanTuneReportCallback exchanges local fitness
→ workers agree on one selected member
→ all ranks enter Trainer.save_checkpoint()
→ only selected rank writes through CheckpointIO
→ Tune receives reports and one Ray checkpoint
→ scheduler verifies the actual checkpoint producer metadata
→ synchronous PBT assigns selected continuation + next genomes
→ resumed train(genome)
→ user restores optimizer history and explicitly reapplies current genome
→ next Lightning run
```

No CBT optimizer applier or restore/application callback participates in the contract.

## Genome ownership evidence

The test's model initially constructs SGD from `genome["lr"]`.

On a resumed invocation, the user-function test code performs the application explicitly:

```python
model.optimizer.load_state_dict(state["optimizer_states"][0])
for param_group in model.optimizer.param_groups:
    param_group["lr"] = genome["lr"]
state["optimizer_states"][0] = model.optimizer.state_dict()
```

The final reported `lr_seen` must equal the current scheduler-controlled genome value.
This proves the next function receives and uses the newly assigned Tune genome while the
optimizer history comes from the selected continuation.

The test does not establish a generic optimizer layout because CBT deliberately does not
own such a layout.

## Population and selection evidence

At each boundary:

- each member contributes its own finite `val_loss` through the already-established
  PyTorch distributed world;
- each worker applies the shared deterministic selection rule;
- the scheduler independently reconstructs the complete stable-member population from
  Tune reports;
- worker-selected winner IDs must agree with scheduler selection;
- exactly the selected member must identify itself as checkpoint source; and
- the producer genome reported to Tune must match the scheduler-controlled subset of that
  trial's active Tune config.

Nested producer configuration is carried through the scheduler result as JSON because
Ray Tune flattens nested result dictionaries before scheduler hooks. That private
representation does not change the user genome.

## Selected checkpoint provenance evidence

The selected Ray checkpoint itself carries metadata under `clan_based_tuning` containing:

- schema version;
- stable producer member ID; and
- the scheduler-controlled genome values that produced the continuation.

Synchronous PBT schedules or resolves the selected source checkpoint before exploiting the
losing targets. `ClanScheduler` uses that point to call `Checkpoint.get_metadata()` on the
actual continuation and rejects the transition unless the checkpoint schema, producer ID,
and producer genome all agree with scheduler state.

The repeated native contract passes through this verification on both report boundaries.
The scheduler therefore verifies the artifact that Ray will redistribute, not merely a
parallel result field claiming which artifact should have been selected.

## Checkpoint storage evidence

The test instruments Lightning's `CheckpointIO` with an audit implementation. Every
physical `save_checkpoint()` call creates one independent audit marker.

Across two members and two completed Clan rounds, the contract requires exactly two audit
markers: one physical Lightning persistence call per round.

Every rank still enters Lightning's public `Trainer.save_checkpoint()`, so all ranks may
construct transient checkpoint dictionaries and participate in its distributed barrier.
Only the selected rank is allowed to delegate the CBT round checkpoint to `CheckpointIO`.
Losing ranks report no Ray checkpoint.

This evidence establishes the CBT storage invariant:

> Persistent CBT continuation checkpoint writes scale with completed rounds, not Clan
> population size.

It does not constrain extra checkpoints deliberately configured by the user outside the
CBT round operation.

## Repeated transition evidence

The run stops only after two Tune `training_iteration` reports per trial. The second
boundary therefore requires a scheduler transition, checkpoint/configuration handoff,
resumed function invocation, userspace genome application, renewed Lightning DDP
training, and another successful population/checkpoint boundary.

The contract establishes repeated operation for this fixed two-member CPU path. It does
not by itself qualify actor reuse, independent member recovery, elastic membership, or a
larger population.

## Framework ownership evidence

Production code on this path:

- does not call `torch.distributed.init_process_group()`;
- does not call `torch.distributed.destroy_process_group()`;
- does not construct a Ray collective group;
- does not select GLOO, NCCL, CPU, or CUDA as a distributed backend;
- does not subclass or replace Lightning `Trainer`;
- does not implement a Ray `Trainable` lifecycle; and
- does not apply the user's genome.

The custom framework seams are limited to:

- a `ClusterEnvironment` carrying externally assigned topology;
- a `DDPStrategy` specialization preserving the cross-trial world and gating the selected
  CBT checkpoint write;
- a Lightning callback consuming the validation boundary and active DDP context; and
- a synchronous PBT specialization replacing population policy while delegating native
  checkpoint/configuration transfer to Ray.

## Non-claims

This evidence does not qualify:

- insufficient-resource/gang admission beyond the current fixed concurrently resident
  population;
- CUDA/NCCL or another accelerator/backend combination;
- multi-node execution;
- actor reuse;
- failure recovery across all distributed lifecycle points;
- arbitrary checkpoint stores or remote storage behavior;
- elastic membership or world-size changes;
- model sharding or ClanFSDP; or
- arbitrary user genome/application correctness.

Those remain separate qualification work when the product claims require them.
