# Framework-alignment evidence ledger

Status: Milestone 1 audit record  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Purpose

This ledger preserves the evidence and reasoning used to propose the dated
[project decisions](../decisions/project_decisions.md). It is an audit record,
not a permanent decision file, milestone gate, or implementation plan.

Existing repository code and tests are treated as proof-of-concept evidence.
They do not determine the accepted architecture merely because they already
exist or pass.

## Evidence classifications

- **Direct source:** behavior visible in pinned upstream source.
- **Probe:** behavior observed in an executable focused test.
- **Inference:** conclusion derived from the Clan mechanism or by combining
  direct sources.
- **Qualification obligation:** behavior that must be proved by the named
  milestone before that milestone may close.

## P1. One trial is one fully resident member

### Ray population generation

**Direct source.** Ray's `BasicVariantGenerator` uses `num_samples` together
with the search space to generate trials and tracks the resulting sample count
and concurrency limit.

- [Ray `BasicVariantGenerator`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/search/basic_variant.py)

**Inference.** A second package population count would duplicate Ray's
configuration and could disagree with the actual generated trial set.

**Alternative considered.** Maintain an independent `population_size` inside
ClanBasedTuning. Rejected because it creates a second authority rather than
constraining Ray's actual population.

### Actor staging

**Direct source.** Ray's Tune controller can stage pending actors through its
resource-management path after consulting the scheduler. Scheduler selection is
not the only admission mechanism.

- [Ray `TuneController`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Inference.** Full-population residency cannot be guaranteed solely by the
scheduler. Admission belongs at the orchestration boundary.

**Qualification obligations.**

- Milestone 3: reject incomplete residency before manual DDP setup.
- Milestone 4: automate the same preflight through the user construction path.

## P2. Lightning produces the evolutionary boundary

### Native validation cadence

**Direct source.** Lightning's training loop decides when validation runs from
Trainer validation configuration, including epoch and subepoch forms.

- [Lightning training-epoch loop](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)
- [Lightning Trainer setup](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/setup.py)

**Inference.** A Clan-owned progress clock would duplicate the training-loop
owner. One qualifying validation report can represent one evolutionary
boundary.

**Alternative considered.** Define rounds through a package epoch, batch,
optimizer-step, or wall-clock counter. Rejected because it duplicates
Lightning cadence and can desynchronize collective members.

### Wall-clock cadence

**Direct source.** Lightning evaluates time-based validation independently in
each process.

- [Lightning time-based validation branch](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)

**Inference.** Runtime jitter can cause members to leave training at different
collective positions. This mode cannot be claimed without direct synchronization
evidence.

**Qualification obligation.** Milestone 3 must prove every supported cadence,
loader, accumulation, and continuation combination.

## P3. Synchronous Ray PBT is the evolutionary foundation

### Population lifecycle

**Direct source.** Ray's synchronous PBT path waits for the live population,
pauses early arrivals, stores results, prepares source checkpoints before
exploitation, transfers source checkpoint/configuration to targets, and resumes
trials through Tune.

- [Ray `PopulationBasedTraining`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Inference.** ClanBasedTuning can change the parent/target policy without
reimplementing the surrounding lifecycle. A singleton source set and all other
members as targets express the Clan transition.

**Alternative considered.** Implement a new population scheduler directly. It
remains the fallback only if Milestone 2 proves the PBT seam cannot express the
Clan policy without substantial Tune-controller duplication.

**Risk.** The likely selection seam is private in Ray 2.56.

**Qualification obligation.** Milestone 2 must pin the seam with an executable
three-or-more-trial, multi-generation contract test before implementation treats
it as stable.

### Experiment restoration

**Direct source.** Ray `Tuner.restore` resumes unfinished trials and can resume
errored trials from their latest checkpoints. Tune persistent storage is
designed to retain experiment state and trial checkpoints for experiment-level
fault tolerance.

- [Ray `Tuner.restore`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/tuner.py)
- [Ray Tune storage documentation source](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/doc/source/tune/tutorials/tune-storage.rst)

**Inference.** Native restoration should be tested before ClanBasedTuning
introduces a generation manifest or recovery transaction. The open question is
whether the specialized synchronous scheduler restores one coherent population
when interruption occurs during a partially assembled boundary.

**Qualification obligations.**

- Milestone 2: test scheduler/trial restoration with synthetic trainables after
  completed and partially assembled population boundaries.
- Milestone 3: repeat with real Lightning model, optimizer, and data state.
- Milestone 6: qualify persistent storage and cluster-failure recovery for the
  industry support envelope.

## P4. Ray transfers state; Lightning defines and restores it

### Lightning report/checkpoint bridge

**Direct source.** Ray's Lightning integration saves a Lightning checkpoint at
validation end and attaches it to `tune.report`. Under FunctionTrainable, a
later save request returns the most recently reported checkpoint.

- [Ray Lightning report/checkpoint callback](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/integration/pytorch_lightning.py)
- [Ray FunctionTrainable checkpoint bridge](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/trainable/function_trainable.py)

**Direct source.** Ray PBT assigns the prepared source checkpoint and new
configuration to exploited target trials.

- [Ray PBT exploitation](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Inference.** Ray can remain authoritative for source selection and transfer;
a second Clan checkpoint scheduler is unnecessary.

**Alternative considered.** Add a Clan checkpoint scheduler or generation
manifest. Rejected absent evidence that native Ray assignment and restoration
fail the milestone contract tests.

### Member-local checkpoint writing

**Direct source.** Lightning's base Strategy writes a checkpoint only on DDP
global rank zero because ordinary replicas are assumed equivalent.

- [Lightning Strategy checkpoint gate](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/strategies/strategy.py)

**Inference.** Every divergent Tune trial must be permitted to write its own
checkpoint because any member may become the parent. A custom `CheckpointIO`
alone cannot bypass a Strategy-level rank gate.

**Qualification obligation.** Milestone 3 must select a nonzero DDP rank as the
parent and prove native report, transfer, and restore behavior.

### Optimizer restoration ordering

**Direct source.** Lightning restores optimizer state through the Strategy and
then restores scheduler state through its checkpoint connector.

- [Lightning checkpoint connector](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/connectors/checkpoint_connector.py)

**Inference.** The receiving member's evolved optimizer values must be applied
after inherited optimizer state is loaded. An independent LR scheduler can
create competing authority over those values.

**Probe.** Existing CPU exploit/restart work shows that inherited optimizer
state and a target learning rate can coexist after restore. It does not
establish the final public seam or broad optimizer support.

**Qualification obligations.**

- Milestone 3: prove the chosen Lightning hook with the narrow supported
  optimizer layout.
- Milestone 5: qualify multiple optimizers, parameter groups, remapping, and
  scheduler interaction.

## P5. Training data is partitioned; fitness data is comparable

**Mechanism inference.** Distinct training batches contribute useful distributed
work to the shared gradient. Candidate fitness must instead be comparable:
different validation samples confound ranking, while distributed metric
reduction combines the candidate scores.

**Framework direction.** Standard PyTorch sampling can express repeated access
to one deterministic evaluation set without a separate data framework.

**Alternatives considered.** A custom evaluation-data subsystem and DDP-reduced
fitness were rejected: the first duplicates standard sampling, while the second
erases the member differences Ray must compare.

- [PyTorch `DistributedSampler`](https://github.com/pytorch/pytorch/blob/4899d123e80a124f31e45ed832bba195af32c353/torch/utils/data/distributed.py)

**Qualification obligation.** Milestone 3 must prove identical validation data,
transforms, ordering, loader length, boundary timing, and one member-local report
per qualifying validation.

## P6. Native DDP owns the shared-gradient substrate

**Direct source.** PyTorch DDP owns parameter verification, initial state
synchronization, gradient hooks, bucketing, and reduction.

- [PyTorch `DistributedDataParallel`](https://github.com/pytorch/pytorch/blob/4899d123e80a124f31e45ed832bba195af32c353/torch/nn/parallel/distributed.py)

**Probe.** Focused PyTorch 2.10 work showed that native DDP can synchronize an
initial state, subsequent buffer broadcasting can be disabled, reduced
gradients remain equal, and different learning rates produce divergent
parameters.

**Inference.** Manual collective and initial-state machinery should be removed
where Lightning can preserve native behavior.

**Alternative considered.** Reimplement gradient communication or initial state
broadcast in ClanBasedTuning. Rejected because Clan requires an ordinary common
gradient, not a new collective algorithm.

**Qualification obligations.**

- Milestone 3: commit the Lightning-facing contract test and qualify the first
  supported precision, accumulation, buffer, and model envelope.
- Milestone 6: repeat under every claimed model-sharding technology.

## P7. Failure and planned completion are collective

### Per-trial stopping order

**Direct source.** Tune evaluates ordinary per-trial stop conditions before the
scheduler completes its result handling.

- [Ray TuneController result handling](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Inference.** One trial may terminate before the synchronous population
transition. Member-local Tune stopping and Lightning early stopping cannot be
accepted without a collective owner.

### Failure handling

**Direct source.** Ray provides trial-error and experiment-stop paths, but
independent recovery does not by itself prove a coherent fixed DDP population.

- [Ray TuneController failure handling](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Mechanism inference.** Losing one participant invalidates both the fixed DDP
world and the population producing the shared gradient.

**Alternatives considered.** Per-trial early stopping, member-local recovery,
and continuing with a smaller population were rejected because each changes the
active collective or population semantics.

**Qualification obligations.**

- Milestone 2: select and test the controller-level collective completion and
  invalid-population outcome.
- Milestone 3: prove distributed termination without indefinite collective
  waits and with useful diagnosis.
- Milestone 6: qualify production failure and recovery behavior.

## Source revisions

- PyTorch: `4899d123e80a124f31e45ed832bba195af32c353`
- Lightning: `7f0c3436cd3f6ad3753125672024fc415cbcb414`
- Ray: `27b0e6a7b88324eab5214a0bc65a839bfbb2dc85`

When a version-sensitive seam changes, update the evidence record, affected
project decision, owning milestone gate, and executable contract test together.
