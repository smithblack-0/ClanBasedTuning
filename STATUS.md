# ClanBasedTuning project status

Last updated: 2026-08-14

## Current implementation

The active function-API branch contains a complete initial Clan Tuning path built on Ray
Tune, Lightning, and PyTorch rather than a package-owned training system.

The implemented pieces are:

- `ClanScheduler`, a synchronous Ray `PopulationBasedTraining` specialization that selects
  one parent continuation and independently mutates that parent genome for every next
  member;
- `ClanScheduler.wrap(train)`, which carries hidden cohort/rendezvous context while
  forwarding Ray's config dictionary unchanged to the user's function;
- `ClanDDPStrategy`, which presents the externally assigned Tune-member topology to
  Lightning, uses the framework's existing distributed backend/process group, preserves
  partitioned training, and replicates Lightning-managed validation across candidates;
- `ClanTuneReportCallback`, which resolves member-local fitness, performs winner-only CBT
  checkpoint persistence, and reports the round to Tune;
- `ClanController`, the framework-independent one-fitness/one-decision primitive used by
  the reporting path;
- `MutationSpec` and the shared deterministic winner-selection policy; and
- the previously qualified `TuneMemberEnvironment` seam for one Tune trial/process per
  Clan member.

Production CBT does not contain a genome-application function, optimizer schema,
optimizer-param-group mapping, application callback, or post-load genome hook. Ray hands
the current genome to the user's function. User code alone decides what that genome means
and how to use it.

## Qualified complete path

A real end-to-end contract runs two concurrent Tune function trials through two successive
Clan generations on one CPU node with:

- Ray 2.56.1;
- Lightning 2.6.5;
- PyTorch 2.10.0; and
- Python 3.11.

The contract establishes that:

- the two Tune trials form one Lightning/PyTorch DDP world;
- both members contribute to one common reduced gradient;
- normal Lightning-managed training remains partitioned between ranks;
- Lightning-managed validation is replicated so both diverged candidates see the same
  complete multi-example held-out set, including the normal sanity-validation setup path;
- member-local optimizer choices produce candidate divergence;
- every member reaches the same population winner through the active distributed context;
- all ranks participate in Lightning checkpoint construction/barrier while only the
  selected rank persists the CBT continuation;
- Ray transfers that selected checkpoint into the next function invocation;
- the receiving user function sees its newly assigned genome and explicitly applies it in
  userspace;
- the selected model state, optimizer momentum, and Lightning `global_step` survive into
  the next generation;
- every next member, including the previous winner, receives an independent mutation of
  the same selected parent genome; and
- persistent CBT checkpoint count scales with completed rounds rather than population
  size times rounds.

The package's dependency-light validation also runs on Python 3.13.

Production code does not select GLOO, NCCL, CPU, or CUDA. GLOO appears only in the CPU
qualification harness through Lightning/PyTorch's ordinary distributed setup.

## Current public boundary

The ordinary path is a Ray function trainable:

```python
def train(genome):
    checkpoint = tune.get_checkpoint()

    if checkpoint is not None:
        # USERSPACE: restore inherited state and use `genome` however your program needs.
        ...

    trainer = pl.Trainer(
        strategy=ClanDDPStrategy(),
        callbacks=[ClanTuneReportCallback()],
        ...,
    )
    trainer.fit(...)
```

`ClanScheduler.wrap(train)` supplies only hidden cohort information. It does not own the
contents or interpretation of `genome`.

The fully qualified Lightning restore example in [`docs/api.md`](docs/api.md) shows one
explicit userspace pattern for applying a changed optimizer genome while retaining
Lightning's complete checkpoint restoration.

For ordinary Lightning-managed dataloaders, training keeps DDP partitioning while the
automatically injected validation sampler is replicated across Clan members. If a user
explicitly supplies a `DistributedSampler`, CBT leaves it alone; that sampler's evaluation
semantics remain userspace.

## Known limits and remaining work

The current complete-path evidence does **not** yet establish:

- CUDA/NCCL execution;
- multi-node execution;
- actor reuse across generations;
- bounded recovery after a member disappears inside an active distributed collective;
- semantics of explicitly user-supplied distributed validation samplers;
- arbitrary/custom/sharded checkpoint plugins;
- model-sharded Clan execution / ClanFSDP; or
- scaled scientific usefulness beyond the mechanics contract.

The candidate fitness metric must remain member-local until CBT's population exchange;
logging it with cross-rank reduction would collapse the candidate distinction selection
needs.

The complete Clan must also be concurrently schedulable. The initial runtime waits for the
whole assigned cohort rather than safely time-multiplexing DDP members; a stronger gang
admission/failure story remains hardening work.

## Current work

The initial CPU mechanics path is implemented and qualified. Current work is final
synchronization/review of that path, followed by cohort/failure hardening and GPU
qualification without changing its userspace boundary.

The active sequence is in [`docs/plan.md`](docs/plan.md). Exact evidence for the complete
function path is recorded in [`docs/qualification/function_api.md`](docs/qualification/function_api.md).

The abandoned PR #51 remains historical evidence only. The clean rebuild is draft PR #52,
branched from the qualified Tune-member Lightning foundation rather than from that
interrupted implementation.

The governing project direction remains [`docs/product_roadmap.md`](docs/product_roadmap.md).
