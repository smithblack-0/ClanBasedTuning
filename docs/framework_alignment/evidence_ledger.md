# Framework-alignment evidence ledger

Status: Milestone 1 audit record under review  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This ledger preserves the source observations, focused probes, inferences,
alternatives, and unresolved questions used to evaluate the proposed
[project decisions](../decisions/project_decisions.md). It is an audit record,
not a decision file, milestone gate, compatibility promise, or implementation
plan.

The milestone gates determine when a project capability must be demonstrated.
This ledger records what the inspected frameworks appear to provide and what
remains uncertain; it does not assign work merely because a framework behavior
was discovered here.

Existing repository code and tests are proof-of-concept evidence. They do not
determine the accepted architecture or support envelope merely because they
already exist or pass.

## Evidence classifications

- **Direct source:** behavior visible in the pinned upstream source.
- **Probe:** behavior observed in an executable focused test.
- **Inference:** a conclusion derived from the Clan mechanism or by combining
  direct observations.
- **Open qualification question:** a material uncertainty that a later design or
  support claim must resolve before relying on it.

An open qualification question is not automatically assigned to the earliest
possible milestone. Its natural home is determined by the roadmap capability
whose completion depends on the answer.

## P1. One trial represents one concurrently live member

### Ray population generation

**Direct source.** Ray's `BasicVariantGenerator` uses `num_samples` and the
search space to generate trials while tracking sample count and concurrency.

- [Ray `BasicVariantGenerator`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/search/basic_variant.py)

**Inference.** A second package-owned population count could disagree with the
actual trial set. The Ray-backed program should derive Clan membership from the
native trial population rather than mirror it.

**Alternative considered.** Maintain an independent `population_size` as the
population authority inside ClanBasedTuning. Rejected because it creates a
second source of truth.

### Actor staging and residency

**Direct source.** Tune's controller can stage pending actors through its
resource-management path after consulting the scheduler. Scheduler policy is not
the only admission mechanism.

- [Ray `TuneController`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Inference.** Full-population residency cannot be guaranteed by the evolutionary
scheduler alone. The orchestration boundary must verify that generated trials,
concurrent resources, and distributed membership describe one live population
before shared-gradient work begins.

**Open qualification question.** Which native Ray resource and trial-state
signals are sufficient for a reliable preflight in the first complete manual
workflow?

## P2. Lightning produces the qualifying round boundary

### Native validation cadence

**Direct source.** Lightning's training loop decides when validation runs from
Trainer configuration, including epoch and subepoch forms.

- [Lightning training-epoch loop](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)
- [Lightning Trainer setup](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/setup.py)

**Inference.** A Clan-owned progress clock would duplicate the training-loop
owner. A qualifying Lightning validation-and-checkpoint event can define the
round boundary.

**Alternative considered.** Define rounds through a package epoch, batch,
optimizer-step, or wall-clock counter. Rejected because it creates a second
cadence and can desynchronize collective members.

### Wall-clock cadence

**Direct source.** Lightning evaluates time-based validation independently in
each process.

- [Lightning time-based validation branch](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)

**Inference.** Runtime jitter may cause members to reach different collective
positions. Time-based validation cannot be included in a support claim without
direct synchronization evidence.

**Open qualification question.** Which validation, accumulation, loader, and
continuation configurations preserve one coherent population boundary?

## Milestone 2 design choice: PBT specialization or direct controller

### Synchronous PBT lifecycle

**Direct source.** Ray's synchronous PBT path waits for the live population,
pauses early arrivals, stores results, prepares source checkpoints before
exploitation, assigns source checkpoint/configuration to targets, and resumes
trials through Tune.

- [Ray `PopulationBasedTraining`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Inference.** A narrow PBT specialization may replace only the population
selection policy while retaining native trial execution.

**Risk.** The likely population-selection seam is version-sensitive and may be
private in Ray 2.56. A subclass that depends on broad internals could be less
maintainable than an independent controller with a thin adapter.

**Alternative retained.** Implement an independently invokable controller and
translate its decision through the narrowest Ray adapter available. This is not
a license to reproduce Tune's pause, resume, checkpoint, resource, or trial
execution lifecycle.

**Open qualification question.** Which option expresses the Clan policy with one
policy authority, independent invocation, minimal version-sensitive surface, and
no substantial Tune lifecycle duplication?

### Experiment restoration

**Direct source.** Ray `Tuner.restore` resumes unfinished trials and can resume
errored trials from their latest checkpoints. Tune persistent storage retains
experiment state and trial checkpoints for experiment-level fault tolerance.

- [Ray `Tuner.restore`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/tuner.py)
- [Ray Tune storage documentation source](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/doc/source/tune/tutorials/tune-storage.rst)

**Inference.** Native experiment restoration must be investigated before the
project invents a Clan generation manifest or recovery transaction.

**Boundary.** This evidence does not make interruption recovery a controller
responsibility. Normal checkpoint-driven next-generation continuation belongs to
the complete integration workflow. Operational interruption recovery is a
support-envelope question for industry qualification.

**Open qualification question.** For each future recovery claim, does native Ray
and Lightning state restore one coherent Clan, fail clearly, or expose a
specific gap requiring approved Clan-specific machinery?

## P3. ClanBasedTuning decides the transition; frameworks execute it

### Report and checkpoint bridge

**Direct source.** Ray's Lightning integration saves a Lightning checkpoint at
validation end and attaches it to `tune.report`. Under FunctionTrainable, a
later save request returns the most recently reported checkpoint.

- [Ray Lightning report/checkpoint callback](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/integration/pytorch_lightning.py)
- [Ray FunctionTrainable checkpoint bridge](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/trainable/function_trainable.py)

**Direct source.** Ray PBT exploitation assigns a prepared source checkpoint and
new configuration to target trials.

- [Ray PBT exploitation](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Inference.** ClanBasedTuning should decide the winning parent. Native Ray
execution can then perform checkpoint/configuration assignment. Saying that Ray
owns “source selection” would incorrectly transfer the Clan policy back to the
framework.

**Alternative considered.** Add a Clan checkpoint scheduler or generation
manifest. Rejected absent direct evidence that native assignment and restoration
cannot satisfy an accepted integration or support contract.

### Member-local checkpoint writing

**Direct source.** Lightning's base Strategy writes a checkpoint only on DDP
global rank zero because ordinary replicas are assumed equivalent.

- [Lightning Strategy checkpoint gate](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/strategies/strategy.py)

**Inference.** When separate Tune trials participate in one DDP collective,
every divergent trial must be able to provide its own checkpoint because any
member may be selected. A custom `CheckpointIO` alone cannot bypass a
Strategy-level rank gate.

**Open qualification question.** What is the narrowest Lightning seam that lets
every candidate report a native trial-local checkpoint without introducing a
second checkpoint system?

### Optimizer restoration ordering

**Direct source.** Lightning restores optimizer state through the Strategy and
then restores scheduler state through its checkpoint connector.

- [Lightning checkpoint connector](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/connectors/checkpoint_connector.py)

**Inference.** The receiving member's evolved optimizer values must be applied
after inherited optimizer state is loaded. A Lightning scheduler that also
writes those fields can create competing authority.

**Probe.** Current CPU exploit/restart evidence shows that inherited optimizer
state and a target learning rate can coexist after restore. It does not certify
the final public hook or broad optimizer layouts.

**Open qualification questions.** Which Lightning hook provides the correct
ordering for the first integration, and which optimizer/scheduler layouts can be
claimed without conflicting authority?

## P4. Training data is partitioned; fitness data is comparable

**Mechanism inference.** Distinct training batches contribute distributed work
to the common gradient. Fitness must instead compare candidate models on the
same workload; different validation samples confound ranking, while distributed
metric reduction combines the candidate scores.

**Framework direction.** Standard PyTorch sampling can express repeated access
to one deterministic evaluation set without a separate data framework.

- [PyTorch `DistributedSampler`](https://github.com/pytorch/pytorch/blob/4899d123e80a124f31e45ed832bba195af32c353/torch/utils/data/distributed.py)

**Alternatives considered.** A custom evaluation-data subsystem and DDP-reduced
fitness were rejected: the first duplicates standard sampling, while the second
erases the candidate differences the controller must compare.

**Open qualification question.** Which sampler, transforms, ordering,
loader-length, boundary timing, and report path establish comparable member-local
fitness in the complete integration?

## P5. Native PyTorch distributed strategies own shared gradients

**Direct source.** PyTorch DDP owns parameter verification, initial state
synchronization, gradient hooks, bucketing, and reduction.

- [PyTorch `DistributedDataParallel`](https://github.com/pytorch/pytorch/blob/4899d123e80a124f31e45ed832bba195af32c353/torch/nn/parallel/distributed.py)

**Probe.** Focused PyTorch and Lightning CPU work showed that native DDP can
synchronize an initial state, runtime buffer broadcasting can be disabled,
reduced gradients remain equal, and different learning rates produce divergent
parameters.

**Inference.** ClanBasedTuning should configure or narrowly specialize the
framework boundary rather than reimplement gradient communication or initial
state transfer where native behavior fits.

**Alternative considered.** Implement a package gradient reducer. Rejected
because Clan Tuning requires an ordinary common gradient, not a new collective
algorithm.

**Open qualification questions.** Which DDP precision, accumulation, buffer,
model, and loader configurations preserve the method? Later, which native
model-sharding strategies can preserve the same semantics without hardcoding a
one-process-per-member architecture?

## P6. Population validity and completion are collective

### Per-trial stopping order

**Direct source.** Tune evaluates ordinary per-trial stop conditions before the
scheduler completes result handling.

- [Ray TuneController result handling](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Inference.** Member-local Tune stopping or Lightning early stopping can remove
a participant before a complete population transition. Such behavior requires a
collective contract rather than ordinary independent stopping.

### Failure handling

**Direct source.** Ray provides trial-error and experiment-stop paths, but
independent trial recovery does not by itself prove a coherent fixed distributed
population.

- [Ray TuneController failure handling](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Mechanism inference.** Losing one required participant invalidates both the
active distributed world and the population producing the shared gradient.

**Alternatives considered.** Per-trial early stopping, silent member-local
recovery, and continuing with a smaller population were rejected because each
changes the active Clan semantics.

**Open qualification questions.** How does the complete integration terminate or
invalidate a broken Clan without indefinite collective waits? Which operational
failure and restoration behaviors can later be included in a published industry
support envelope?

## Current proof-of-concept evidence

The current repository demonstrates useful mechanisms but does not certify the
proposed architecture or later milestone exits.

- `tests/framework_contracts/test_ray_native_pbt_cycle.py` exercises a small
  native Tune/Lightning/PBT exploit-and-restore cycle. It supports feasibility of
  the current Ray/Lightning path but does not decide the final controller form,
  prove experiment interruption recovery, or establish a broad support range.
- Existing CPU distributed probes support common gradients with optimizer-driven
  divergence, member-local state, and exploit-style restore ordering. Their
  conclusions remain mechanism evidence until retained tests and documentation
  identify the exact public contract they qualify.
- Existing examples demonstrate proof-of-concept composition. They are not
  milestone examples unless they use the accepted public path and perform the
  reader and evidence job required by that milestone.

## Source revisions

- PyTorch: `4899d123e80a124f31e45ed832bba195af32c353`
- Lightning: `7f0c3436cd3f6ad3753125672024fc415cbcb414`
- Ray: `27b0e6a7b88324eab5214a0bc65a839bfbb2dc85`

These exact revisions make the research reproducible. They do not pin the
published package to one exact dependency version. Future compatibility claims
must be backed by version-specific contract tests and expressed as the support
range those tests actually establish.
