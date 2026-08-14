# ClanBasedTuning project status

Last updated: 2026-08-14

## Current implementation

The active function-API branch contains the first repeated Ray Tune + Lightning Clan
workflow.

The package includes:

- `ClanController`, with one local fitness, one population exchange, one cached
  checkpoint-source decision, and the resolved winner identity;
- the shared deterministic winner-selection function;
- `MutationSpec`;
- `ClanScheduler`, a synchronous Ray PBT specialization implementing the Clan
  single-parent population policy;
- `ClanScheduler.wrap(train)`, which supplies hidden stable-member and rendezvous context
  without modifying the user's `train(genome)` argument;
- `TuneMemberEnvironment` and `ClanDDPStrategy` for one externally launched Tune process
  per Clan DDP rank; and
- `ClanTuneReportCallback` for member-local fitness exchange, winner agreement, one
  distributed Lightning checkpoint boundary, and Tune reporting.

There is no CBT optimizer applier or post-restore optimizer callback. The Tune genome is
userspace configuration. On resume, the user's function restores inherited state and
explicitly applies its newly assigned genome.

## Direct framework evidence

The current native contracts use Ray 2.56.1, Lightning 2.6.5, PyTorch 2.10.0, Python 3.11,
and single-node CPU execution.

The topology contract proves that two concurrent Tune function trials can become two
externally launched Lightning/PyTorch DDP ranks and receive the same reduced gradient.

The repeated function-API contract additionally performs two Clan report boundaries and
proves that:

- the complete two-member population reaches one shared DDP training world;
- local fitness values are exchanged through that already-established PyTorch distributed
  context;
- workers and the Tune scheduler agree on one selected member;
- only the selected rank delegates the CBT round checkpoint to Lightning `CheckpointIO`;
- instrumented `CheckpointIO` observes exactly one physical Lightning checkpoint write
  per Clan round, not one per member;
- Ray's synchronous PBT lifecycle transfers the selected continuation and target genome;
- a resumed user function restores inherited optimizer history and explicitly reapplies
  the newly assigned genome; and
- the next generation reaches the same public reporting path successfully.

The test does not specify a production process-group backend. `ClanDDPStrategy` leaves
ordinary Lightning/PyTorch backend selection intact. The earlier CPU topology contract
observes GLOO when the test explicitly requests it; that test-only choice is not production
policy.

## Current userspace contract

Ordinary use is PBT-shaped:

```python
def train(genome):
    checkpoint = tune.get_checkpoint()
    if checkpoint is not None:
        ... restore selected parent optimizer history ...
        ... explicitly apply this member's current genome ...

    trainer = Trainer(
        strategy=ClanDDPStrategy(),
        callbacks=[ClanTuneReportCallback()],
        ...,
    )
    trainer.fit(...)
```

The complete application code is retained in
[`examples/simple_clan_tuning.py`](examples/simple_clan_tuning.py) and
[`docs/api.md`](docs/api.md). CBT does not infer that a genome key is a learning rate,
weight decay, scheduler field, or any other training-system property.

The scheduler is constructed separately and wraps the ordinary function:

```python
scheduler = ClanScheduler(...)
trainable = scheduler.wrap(train)
```

Private Clan topology remains outside the genome dictionary.

## Checkpoint storage behavior

Every DDP rank enters Lightning's public `Trainer.save_checkpoint()` because that
operation contains a distributed barrier. Each rank may therefore build transient
checkpoint state in memory.

During the scoped CBT round checkpoint, `ClanDDPStrategy` permits only the selected rank
to call the configured `CheckpointIO.save_checkpoint()`. Losing ranks persist no CBT
checkpoint and report no Ray checkpoint. Persistent CBT continuation storage therefore
scales with completed rounds, not population size.

Ordinary additional Lightning checkpointing configured by the user is outside this CBT
storage guarantee.

## Framework ownership

- Ray Tune owns trial execution, resources, synchronous PBT lifecycle, checkpoint
  registration/reassignment, and configuration transfer.
- `ClanScheduler` owns stable Clan assignment, authoritative winner verification, genome
  mutation, and mutation random state.
- the hidden coordinator owns only stable member mapping and per-invocation rendezvous
  facts;
- Lightning/PyTorch own process-group initialization, backend/device behavior, shared
  gradients, collectives, checkpoint construction, restore semantics, and barriers;
- `ClanDDPStrategy` supplies the external topology and winner-only CBT write gate without
  selecting the distributed backend; and
- user code owns genome interpretation and application.

Production CBT does not call `torch.distributed.init_process_group()`,
`torch.distributed.destroy_process_group()`, or Ray collective-group construction.

## Current limitations

The directly qualified path is intentionally narrow. It does not yet establish support
for:

- CUDA/NCCL or other accelerator paths;
- multi-node execution;
- flexible gang admission when the cluster cannot already run the complete Clan
  concurrently;
- actor reuse;
- complete failure/recovery behavior across every distributed lifecycle point;
- arbitrary optimizer/application layouts beyond the fact that CBT leaves those layouts
  to userspace; or
- later ClanFSDP/model-sharded execution.

The current coordinator times out rather than silently shrinking an incomplete Clan. The
broader cohort-admission and failure requirements in the qualification contract remain
open before a wider production support claim.

## Current review work

Draft PR #51, `Build the Clan Tune function API`, is the active review unit. It is stacked
on draft PR #50's qualified `TuneMemberEnvironment` seam and remains unmerged.

The next work is final source-order/adversarial review of the function path and its public
example, followed by exact-head CI and documentation/evidence cleanup. No CI workflow
changes are planned.

The governing product direction remains [`docs/product_roadmap.md`](docs/product_roadmap.md).
Current design and contracts are indexed by [`docs/README.md`](docs/README.md).
