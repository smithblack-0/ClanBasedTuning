# Framework-alignment evidence ledger

Status: referential audit record  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

This ledger supports the decisions in
[`decision_register.md`](decision_register.md). It records the upstream behavior
reviewed, the inference drawn from it, and the qualification still required.
It is not the primary explanation or an implementation plan.

## Evidence classifications

- **Direct source:** behavior visible in the pinned upstream source.
- **Probe:** behavior observed in an executable focused test.
- **Inference:** conclusion derived from the mechanism or from combining direct
  sources; it still requires later implementation verification where noted.
- **Deferred:** material risk whose solution is outside the current milestone.

## D1. One trial is one fully resident member

### Ray population generation

**Direct source.** Ray's `BasicVariantGenerator` uses `num_samples` together
with the search space to generate trials and tracks the resulting total sample
count and concurrency limit.

- [Ray `BasicVariantGenerator`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/search/basic_variant.py)

**Inference.** A second package population count would duplicate Ray's
configuration and could disagree with the actual generated trial set. The
initial topology should therefore keep search generation simple enough that
`num_samples` remains the member count and can be checked against the generated
population.

### Actor staging

**Direct source.** Ray's Tune controller can stage pending actors through its
resource-management path after consulting the scheduler. Scheduler selection is
not the only admission mechanism.

- [Ray `TuneController`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Inference.** Full-population residency cannot be guaranteed solely by the
Clan scheduler. The later assembly path must inspect population, concurrency,
per-trial resources, and available dedicated allocation before DDP setup.

**Required qualification.** Reject insufficient concurrency or devices before
any member enters the process group.

## D2. Lightning owns the round boundary

### Native validation cadence

**Direct source.** Lightning's training loop decides when validation runs from
Trainer validation configuration, including epoch and subepoch forms.

- [Lightning training-epoch loop](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)
- [Lightning Trainer setup](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/setup.py)

**Inference.** A Clan-owned progress counter would duplicate the training-loop
owner. One qualifying validation report can instead represent one evolutionary
boundary.

### Wall-clock cadence

**Direct source.** Lightning evaluates time-based validation independently in
each process.

- [Lightning time-based validation branch](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/loops/training_epoch_loop.py)

**Inference.** Runtime jitter can cause one Clan member to leave training while
another still expects training collectives. Wall-clock cadence should not be an
initial support claim.

**Required qualification.** Demonstrate synchronized subepoch validation and
exact continuation for every supported loader configuration.

## D3. Synchronous Ray PBT is the evolutionary foundation

### Synchronous population lifecycle

**Direct source.** Ray's synchronous PBT path waits for the live population,
pauses early arrivals, stores scores, prepares source checkpoints before
exploitation, transfers source checkpoint and configuration to targets, and
resumes trials through Tune.

- [Ray `PopulationBasedTraining`](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/schedulers/pbt.py)

**Inference.** ClanBasedTuning can change parent and target selection without
reimplementing the surrounding lifecycle. A singleton source set and all other
members as targets express the Clan transition conceptually.

**Risk.** The likely selection seam is private in Ray 2.56. A narrow
specialization is still preferable to a new scheduler only if executable tests
pin the expected behavior.

**Required qualification.** At least three trials, deterministic ties, one
elite, all nonwinners targeted, two consecutive generations, and source
checkpoint ordering.

## D4. Ray transfers checkpoints; Lightning defines and restores them

### Lightning report and checkpoint bridge

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

### Member-local checkpoint writing

**Direct source.** Lightning's base Strategy writes a checkpoint only on DDP
global rank zero because ordinary replicas are assumed equivalent.

- [Lightning Strategy checkpoint gate](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/strategies/strategy.py)

**Inference.** Every divergent Tune trial must be permitted to write its own
checkpoint because any member may become the parent. A custom `CheckpointIO`
alone cannot bypass a Strategy-level rank gate.

**Required qualification.** Use Ray's standard callback with the narrowest
Lightning Strategy seam and select a nonzero DDP rank as the source.

### Optimizer restoration ordering

**Direct source.** Lightning restores optimizer state through the Strategy and
then restores scheduler state through its checkpoint connector.

- [Lightning checkpoint connector](https://github.com/Lightning-AI/pytorch-lightning/blob/7f0c3436cd3f6ad3753125672024fc415cbcb414/src/lightning/pytorch/trainer/connectors/checkpoint_connector.py)

**Inference.** The receiving member's evolved optimizer values must be applied
after inherited optimizer state is loaded. An independent LR scheduler would
continue modifying the same values and create competing authority.

**Probe evidence.** The repository's existing CPU exploit/restart work provides
proof-of-concept evidence that inherited optimizer state and a target learning
rate can coexist after restore. It does not yet establish the final public seam
or broader optimizer support.

**Required qualification.** SGD momentum, AdamW moments, unsupported mapping
failure, and the chosen Lightning restore hook.

## D5. Training data is partitioned; fitness data is replicated

**Mechanism inference.** Distinct training batches contribute useful distributed
work to the shared gradient. Candidate fitness must instead be comparable:
different validation samples would confound ranking, and distributed metric
reduction would combine the candidate scores.

**Framework direction.** Standard PyTorch sampling can express repeated access
to one deterministic evaluation set without a separate data framework.

- [PyTorch `DistributedSampler`](https://github.com/pytorch/pytorch/blob/4899d123e80a124f31e45ed832bba195af32c353/torch/utils/data/distributed.py)

**Required qualification.** Identical validation dataset, transforms, ordering,
loader length, boundary timing, and one member-local report per qualifying
validation.

## D6. Native DDP owns the shared-gradient substrate

**Direct source.** PyTorch DDP owns parameter verification, initial state
synchronization, gradient hooks, bucketing, and reduction.

- [PyTorch `DistributedDataParallel`](https://github.com/pytorch/pytorch/blob/4899d123e80a124f31e45ed832bba195af32c353/torch/nn/parallel/distributed.py)

**Probe evidence.** Focused PyTorch 2.10 probing showed that native DDP can
synchronize an initial state, subsequent buffer broadcasting can be disabled,
reduced gradients remain equal, and different learning rates produce divergent
parameters.

**Inference.** Manual collective and initial-state machinery should be removed
where the Lightning integration can preserve this native behavior.

**Required qualification.** Commit the exact Lightning-facing contract test and
separately qualify accumulation, precision, buffers, and any altered reduction
semantics before claiming support.

## D7. Failure and planned completion are collective

### Per-trial stopping order

**Direct source.** Tune evaluates ordinary per-trial stop conditions before the
scheduler completes its result handling.

- [Ray TuneController result handling](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Inference.** One trial may terminate before the synchronous population
transition. Member-local Tune stopping and Lightning early stopping are
therefore incompatible with the initial Clan lifecycle.

### Failure handling

**Direct source.** Ray provides trial-error and experiment-stop paths, but those
paths do not make independently recovered actors coherent members of the
current DDP generation.

- [Ray TuneController failure handling](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Mechanism inference.** Losing one participant invalidates both the fixed DDP
world and the population producing the shared gradient. Initial behavior must
fail or stop together.

**Required qualification.** Select one collective planned-completion owner and
verify that one member error terminates the complete Clan without indefinite
collective waits.

## D8. Whole-experiment recovery is deferred

**Direct source.** Ray handles individual actor events and may checkpoint the
whole experiment afterward. A persisted snapshot can therefore fall between
member reports at a synchronous boundary.

- [Ray TuneController step and experiment checkpoint](https://github.com/ray-project/ray/blob/27b0e6a7b88324eab5214a0bc65a839bfbb2dc85/python/ray/tune/execution/tune_controller.py)

**Inference.** Ordinary PBT can tolerate independently located trial state;
Clan Tuning cannot assume such a snapshot identifies one committed generation.
Normal winner checkpoint inheritance remains usable, but interrupted-round
experiment recovery requires a later authority and transaction design.

## D9. Current code is evidence, not architecture

**Governing source.** The project roadmap identifies the repository as pre-alpha
proof-of-concept work and makes framework-alignment research the basis for later
design.

- [Product roadmap](../product_roadmap.md)

**Consequence.** Passing current tests establishes evidence about mechanisms. It
does not grant current classes, configuration surfaces, or file boundaries
contractual authority.

## Source revisions

- PyTorch: `4899d123e80a124f31e45ed832bba195af32c353`
- Lightning: `7f0c3436cd3f6ad3753125672024fc415cbcb414`
- Ray: `27b0e6a7b88324eab5214a0bc65a839bfbb2dc85`

The project's dependency ranges remain authoritative for the supported version
window. When a version-sensitive seam changes, update this ledger, its dependent
decision, and the executable contract test together.
