# Framework-alignment evidence ledger

Status: milestone-one audit track  
Date: 2026-07-24  
Purpose: preserve the evidence, rejected alternatives, confidence, and remaining
probe behind each framework-alignment conclusion.

## Classification

- **Accepted direction:** strong enough to plan against after human review.
- **Implementation gate:** plausible direction whose support depends on an
  executable contract test.
- **Deferred capability:** real lifecycle concern outside the initial supported
  system.
- **Rejected:** duplicates framework ownership or conflicts with Clan Tuning.

Source links are pinned to the upstream revisions reviewed for the dependency
ranges in `pyproject.toml`.

## 1. Lightning owns round cadence

**Classification:** Accepted direction

**Evidence.** Lightning 2.6 decides when to enter validation from
`check_val_every_n_epoch`, `val_check_interval`, and its time-interval setting.
The decision is made in the native training loop, not by a callback or external
scheduler.

- [Lightning training-loop validation decision](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)
- [Lightning Trainer validation configuration](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/setup.py)

**Alternative considered.** A Clan-owned epoch, optimizer-step, batch, or time
counter that requests evaluation.

**Decision.** Rejected. It would create a second validation schedule and force
ClanBasedTuning to translate training progress already owned by Lightning.

**Remaining evidence.** Qualify the deterministic subepoch modes whose loop and
data position restore correctly after Tune pauses and recreates the trial.

## 2. Wall-clock validation is not a safe initial cadence

**Classification:** Accepted direction

**Evidence.** Lightning checks the elapsed wall-clock interval independently
inside each process. Clan members are also ranks in one training collective.
Runtime jitter can therefore make one member leave training for validation while
another remains in training collectives.

- [Lightning time-based validation branch](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)

**Alternative considered.** Treat every Lightning-supported validation cadence
as automatically supported by ClanBasedTuning.

**Decision.** Rejected. Framework ownership does not imply that every framework
configuration preserves the Clan collective.

**Remaining evidence.** A failure probe would improve diagnostics, but no such
probe is required to avoid advertising wall-clock cadence initially.

## 3. One qualifying report can be one PBT decision opportunity

**Classification:** Accepted direction

**Evidence.** Ray PBT accepts a monotonic `time_attr`. Tune's
`training_iteration` advances with reported training results, so report count can
represent successive Lightning-owned evaluation events without measuring the
training work between them.

- [Ray PBT progress contract](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)
- [Ray FunctionTrainable reporting](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/trainable/function_trainable.py)

**Alternative considered.** Expose a separate PBT perturbation interval in
addition to Lightning's evaluation cadence.

**Decision.** Rejected. It creates two user-facing controls for one round
boundary.

**Remaining evidence.** Verify that the supported integration emits no unrelated
Tune reports that could advance PBT.

## 4. Synchronous PBT supplies the population lifecycle

**Classification:** Accepted direction

**Evidence.** Stock synchronous PBT waits for all live trials, pauses early
arrivals, records scores, orders source checkpointing before target exploitation,
transfers source checkpoints and configurations, and leaves the population
paused for rescheduling.

- [Ray PBT synchronous result handling and exploitation](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Alternative considered.** Implement a new controller directly from
`TrialScheduler`.

**Decision.** Rejected unless executable probes invalidate the narrow PBT seam.
A fresh controller would use more Tune controller internals and duplicate more
lifecycle behavior.

**Remaining evidence.** Three-member and repeated-generation probes.

## 5. One winner and all targets can use a narrow PBT override

**Classification:** Implementation gate

**Evidence.** Stock PBT chooses an exploitation source from the upper population
and applies exploitation to the lower population. A singleton upper population
makes the source deterministic; placing every other live member in the lower
population expresses the Clan transition.

- [Ray PBT quantile and exploit implementation](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Alternative considered.** A custom generation coordinator outside Ray PBT.

**Decision.** The narrow override is the leading design. The seam is private in
Ray 2.56, so version pinning, explicit comments, and executable contract tests
are mandatory.

**Remaining evidence.** Ties, three or more members, two consecutive
generations, elite behavior, and source-checkpoint ordering.

## 6. Ray selects and transfers checkpoints; Lightning defines them

**Classification:** Accepted direction

**Evidence.** Ray's Lightning callback saves a Lightning checkpoint and reports
it with metrics. FunctionTrainable returns the latest reported checkpoint when
PBT later requests a save. PBT then assigns the selected source checkpoint to
its targets.

- [Ray Lightning report/checkpoint callback](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/integration/pytorch_lightning.py)
- [Ray FunctionTrainable checkpoint bridge](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/trainable/function_trainable.py)
- [Ray PBT checkpoint transfer](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Alternative considered.** A Clan checkpoint scheduler, generation manifest, or
second checkpoint transfer path.

**Decision.** Rejected for the initial system. It would duplicate both
frameworks.

**Remaining evidence.** Benchmark checkpoint cost and later qualify remote
storage.

## 7. Every member needs a trial-local Lightning checkpoint

**Classification:** Accepted direction

**Evidence.** Lightning's base Strategy writes only on DDP global rank zero.
Ordinary DDP assumes equivalent replicas; Clan members are divergent Tune trials,
and any member may be selected as the parent.

- [Lightning Strategy checkpoint gate](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/strategies/strategy.py)

**Alternative considered.** Use default DDP checkpointing unchanged.

**Decision.** Rejected. The integration needs a narrow Lightning seam that lets
each Tune trial write its own local candidate checkpoint.

**Remaining evidence.** Prove the Strategy override through Ray's standard
callback and select a non-DDP-global-zero member as the PBT source.

## 8. Optimizer configuration belongs after inherited state restoration

**Classification:** Accepted direction

**Evidence.** Lightning restores optimizer state through
`strategy.load_optimizer_state_dict` and then restores LR scheduler state.
Applying the receiving trial's configuration after optimizer restoration retains
the winner's moments while establishing the target optimizer policy.

- [Lightning checkpoint restoration ordering](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/connectors/checkpoint_connector.py)

**Alternative considered.** Mutate optimizer values before restore or rebuild the
optimizer from scratch.

**Decision.** Rejected. Restore would overwrite the former; the latter would
discard inherited optimizer state.

**Remaining evidence.** SGD momentum and AdamW moment inheritance probes.

## 9. Independently acting LR schedulers are initially incompatible

**Classification:** Accepted direction

**Evidence.** Lightning restores and resumes LR scheduler state after optimizer
state restoration. An ordinary scheduler would continue changing values that
Clan evolution also owns.

- [Lightning optimizer and scheduler restoration](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/connectors/checkpoint_connector.py)

**Alternative considered.** Permit ordinary schedulers without defining their
relationship to Clan mutations.

**Decision.** Rejected for initial support. A future combined policy may support
them, but it must establish one authority.

**Remaining evidence.** None for the initial restriction.

## 10. Ray's `num_samples` should be the initial population authority

**Classification:** Accepted direction

**Evidence.** Ray already exposes `TuneConfig.num_samples` as the ordinary
population input. `BasicVariantGenerator` records the resulting generated
`total_samples` and exposes its concurrency cap. Initial support should require
`max_concurrent_trials == num_samples`. Grid expansion can make the
generated count exceed `num_samples`, so it complicates preflight without adding
value to the first Clan topology.

- [Ray BasicVariantGenerator](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/search/basic_variant.py)

**Alternative considered.** Require a separate Clan `population_size`, or allow
grid-expanded and alternate-search populations immediately.

**Decision.** Both are rejected initially. Use Ray `num_samples`, require the
default variant generator with no grid expansion, and defensively verify that
`total_samples` matches before the collective forms, and require the Ray
concurrency cap to equal that population.

**Remaining evidence.** Verify fresh-run and restore behavior through the public
assembly path.

## 11. Full residency must be validated before DDP begins

**Classification:** Accepted direction

**Evidence.** Ray's controller can stage pending actors independently after
consulting the scheduler. The scheduler's `choose_trial_to_run` decision is not
the sole actor-admission path.

- [Ray TuneController actor staging](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Alternative considered.** Let the Clan scheduler alone prevent partial
population admission.

**Decision.** Rejected. The primary check belongs at an assembly boundary that
can inspect the generated population, concurrency, resource request, and
available dedicated allocation before `Tuner.fit()`.

**Remaining evidence.** Define and test the preflight against the supported
single-node GPU topology.

## 12. Fitness data is replicated and fitness remains member-local

**Classification:** Accepted direction

**Evidence.** Clan members are distinct candidate models. Partitioned validation
would compare different samples, while DDP-synchronized fitness would erase the
member differences. PyTorch's standard sampler can represent one replicated
logical shard without a new sampler subsystem.

**Alternative considered.** A custom fitness sampler framework or
`sync_dist=True` fitness.

**Decision.** Both are rejected for the initial system. Use standard PyTorch data
primitives and keep the fitness scalar local to the Tune trial.

**Remaining evidence.** End-to-end deterministic validation comparison.

## 13. Native DDP should own initialization where qualified

**Classification:** Implementation gate

**Evidence.** PyTorch DDP provides parameter-shape verification and initial
parameter and buffer synchronization. A local two-process PyTorch 2.10 probe
confirmed initial synchronization, disabled later buffer broadcasts, common
reduced gradients, and parameter divergence after applying different learning
rates.

- [PyTorch DistributedDataParallel](https://github.com/pytorch/pytorch/blob/4899d123e80a124f31e45ed832bba195af32c353/torch/nn/parallel/distributed.py)

**Alternative considered.** Manual model-schema gathering and initial broadcast.

**Decision.** Native DDP is the leading owner. Manual duplication should remain
only if the Lightning integration probe demonstrates a real gap.

**Remaining evidence.** Commit the probe as a reproducible framework-contract
test and verify the exact Lightning hook.

## 14. Precision support is unresolved

**Classification:** Implementation gate

**Evidence.** No committed probe establishes the behavior of dynamic loss
scaling across intentionally divergent members. Ordinary DDP support is not
sufficient evidence because the replicas normally apply equivalent updates.

**Alternative considered.** Reject FP16 from assumption, or accept it because
standard DDP supports it.

**Decision.** Both are rejected. Precision support must be based on direct
multi-round divergent-member probes. BF16 is the leading candidate, not yet a
gate.

**Remaining evidence.** FP16 scaler and overflow behavior plus BF16 multi-round
training.

## 15. Per-trial stopping is incompatible

**Classification:** Accepted direction

**Evidence.** Tune evaluates per-trial stopping before invoking the scheduler.
One member can therefore terminate before the synchronous controller completes
the population decision.

- [Ray TuneController result ordering](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Alternative considered.** Ordinary `RunConfig(stop=...)` or member-local
Lightning early stopping.

**Decision.** Rejected. Planned completion must be collective and occur at a
synchronized population boundary.

**Remaining evidence.** Select and test one collective completion owner in
milestone two.

## 16. One member failure invalidates the active clan

**Classification:** Accepted direction

**Evidence.** The shared DDP gradient and fixed population require every member.
Ray exposes scheduler error handling and experiment-wide stop paths, but
independent trial recovery would resume one member outside the current
collective state.

- [Ray TuneController failure handling](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Alternative considered.** Recover one member independently or shrink the DDP
world.

**Decision.** Rejected for initial support. Both change the algorithm or its
collective.

**Remaining evidence.** Failure propagation after manual orchestration exists.

## 17. Whole-experiment restoration is a deferred capability

**Classification:** Deferred capability

**Evidence.** Tune processes individual actor events and may then persist the
experiment state. It can therefore capture a synchronous boundary after some
members have reported and before the full population decision completes.

- [Ray TuneController step and experiment checkpoint](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Alternative considered.** Add rollback normalization, shared retention, or a
durable generation transaction to the initial system.

**Decision.** Deferred. The lifecycle hazard is documented, but recovery
machinery is not needed for the first functional Clan workflow.

**Remaining evidence.** Later interrupted-boundary recovery design and tests.

## 18. Existing source has no architectural presumption

**Classification:** Accepted direction

**Evidence.** The governing roadmap identifies the repository as pre-alpha
proof-of-concept evidence and makes framework-alignment research authoritative
for later design.

- [Governing product roadmap](../product_roadmap.md)

**Alternative considered.** Preserve current classes because they already run.

**Decision.** Rejected. Code may be reused only where its contract independently
satisfies the accepted gates.

**Remaining evidence.** Human acceptance of this research package.

## Focused probe completed during research

### PyTorch DDP initialization and divergence

A local two-process PyTorch 2.10 probe established:

1. rank-local parameters and buffers began with different values;
2. native DDP initialization synchronized parameters and buffers from rank zero;
3. disabling `broadcast_buffers` on the constructed wrapper prevented later
   forward-time buffer synchronization;
4. DDP produced the same reduced gradients on both ranks;
5. different learning rates produced different parameters.

This supports the native-DDP direction. It is not yet durable project evidence
because the script and assertions are not committed. Milestone-one completion
must convert it into a framework-contract test or lower the conclusion to
unresolved.

## Required probes before the next support claims

1. One-winner/all-target PBT transition with at least three trials.
2. Two consecutive generations with deterministic winner, elite behavior, and
   independently mutated target configurations.
3. Every member checkpointing through Lightning's validation callback despite
   DDP global-rank-zero defaults.
4. SGD momentum and AdamW moment inheritance followed by target configuration
   reconciliation.
5. Subepoch validation, pause, checkpoint, process recreation, and exact
   continuation for the chosen supported dataloader configuration.
6. Replicated deterministic fitness data with member-local metrics.
7. Full-residency preflight rejecting insufficient devices or concurrency before
   any member enters DDP.
8. One member failure causing collective failure without independent recovery.
9. Collective planned completion at a synchronized population boundary.
10. BF16 and FP16 behavior under intentionally divergent members.

## Source scope

- Project dependency contract: [`pyproject.toml`](../../pyproject.toml)
- Governing product contract: [`product_roadmap.md`](../product_roadmap.md)
- PyTorch revision: `4899d123e80a124f31e45ed832bba195af32c353`
- Lightning revision: `7f0c3436cd3f6ad3753125672024fc415cbcb414`
- Ray revision: `27b0e6a7b88324eab5214a0bc65a839bfbb2dc85`
