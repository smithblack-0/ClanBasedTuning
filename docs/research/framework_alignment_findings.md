# Framework-alignment findings

Status: proposed milestone-one research conclusions for human review  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Executive decision

ClanBasedTuning should specialize existing Ray Tune, Lightning, and PyTorch
lifecycles rather than introduce a parallel training system.

The framework split that survives review is:

- Ray Tune owns trials, synchronous population scheduling, checkpoint transfer,
  pause, resume, and trial configuration.
- Lightning owns training, validation cadence, validation execution, checkpoint
  contents, restoration, optimizer construction, and dataloader integration.
- PyTorch DDP owns process-group collectives, gradient reduction, and as much
  initialization synchronization as its supported contract permits.
- ClanBasedTuning owns only the semantic differences required by Clan Tuning:
  one Tune trial per member, cross-trial DDP membership, one-parent population
  transition, optimizer-configuration reconciliation after restore, collective
  failure and stopping behavior, and setup checks required by full concurrent
  residency.

This conclusion is architectural, not an endorsement of the current source
layout. The repository code remains proof-of-concept evidence and may be
rewritten wherever its contracts do not survive this research.

## System contract

A clan is one collective training entity composed of a fixed population of Tune
trials. Every live member participates in every pooled training gradient.
Members begin a round from one inherited model and optimizer state, train on
separate data through a common reduced gradient, apply that gradient through
member-local optimizer configuration and state, and compete on the same held-out
data. One winner supplies the model parameters, optimizer state, and optimizer
configuration from which the next generation begins.

A queued or time-multiplexed member is not a degraded operating mode. It is a
different algorithm: the absent member cannot contribute to each gradient
without stale-gradient storage or per-step model swapping. Full concurrent
residency is therefore foundational.

## Round lifecycle

### Decision

A round is the interval between two qualifying Lightning evaluation-and-
checkpoint events. Lightning owns when those events occur.

ClanBasedTuning must not introduce an epoch counter, optimizer-step counter,
batch conversion, timer, or second validation schedule to define the round.
Lightning already supports epoch and subepoch validation through its Trainer
configuration. Ray PBT should treat each qualifying report as one population
decision opportunity.

The intended mapping is:

1. Lightning trains according to the user's Trainer configuration.
2. Lightning enters a qualifying validation loop at its configured cadence.
3. Every member evaluates the same held-out data.
4. Every member produces one member-local Lightning checkpoint and one fitness
   report.
5. Synchronous PBT waits until the complete live population has reported.
6. The controller selects one winner and assigns the winner's checkpoint as the
   source for every next-generation member.
7. Ray resumes the trials; Lightning restores the inherited state; the receiving
   member's optimizer configuration is reapplied.

Ray's `training_iteration` may count these reports internally. It does not define
how much training belongs to a round.

### Support consequence

Subepoch rounds are required for practical Clan Tuning because an epoch may be
far too long for the pooled gradient to remain useful to diverging members.
However, not every Lightning validation mode is automatically safe.

All members must enter validation at the same training-loop location. A
batch-based or fractional cadence can be qualified when every member has the
same loop length and deterministic boundary. Independent wall-clock validation
is a poor initial candidate because runtime jitter can make one DDP rank leave
training while another rank is still executing training collectives.

The exact supported Lightning cadence and exact subepoch continuation behavior
remain milestone-three integration gates. The ownership decision does not.

## Evolutionary controller

### Decision

The evolutionary subsystem should subclass Ray Tune's synchronous
`PopulationBasedTraining` unless executable contract probes invalidate the
required seam.

Stock synchronous PBT already owns the needed lifecycle: it waits for the
population, records scores, checkpoints source trials before exploitation,
transfers a source checkpoint and configuration to target trials, pauses the
population, and resumes the trials through Tune.

ClanBasedTuning changes the population decision, not the surrounding lifecycle:

- choose exactly one deterministic winner;
- treat every other live member as a target;
- preserve one unmutated elite configuration consistently;
- generate optimizer-only mutations for the remaining members;
- reject missing or non-finite fitness;
- use a documented deterministic tie rule;
- require the complete live population at the decision boundary.

The implementation is expected to use a narrow PBT override. Because the likely
selection seam is private in Ray 2.56, the package must pin the supported Ray
range and maintain executable source-contract tests. Reimplementing the entire
scheduler would use more private Tune controller operations, duplicate more
lifecycle behavior, and create a larger maintenance burden.

### Documentation requirement

The controller must explain that it is not ordinary quantile PBT. A blind reader
must be able to identify the sole-parent transition, elite rule, mutation scope,
fitness requirements, and collective failure behavior from the class contract
without reading Ray internals.

## Checkpoint and restore ownership

### Population transition

Ray PBT owns which checkpoint is selected and where it is transferred.
Lightning owns the contents of each member checkpoint.

Ray's Lightning integration reports a Lightning checkpoint with the validation
metrics. Under the FunctionTrainable path, a later PBT save request returns that
already reported checkpoint rather than invoking a second Lightning save. This
allows the normal PBT exploitation path to remain authoritative.

Every member must nevertheless be able to produce its own candidate checkpoint.
Lightning's base Strategy writes only on DDP global rank zero because ordinary
DDP replicas are assumed equivalent. Clan members are intentionally divergent
and each Tune trial may become the winner. The integration therefore needs a
narrow Lightning checkpoint seam that permits each member to write its own
trial-local checkpoint.

The leading implementation is Ray's standard
`TuneReportCheckpointCallback` plus a narrowly specialized Lightning Strategy
checkpoint method. This is a milestone-three design conclusion, not a reason to
add a Clan checkpoint scheduler, manifest, or second retention system.

### Optimizer restoration

Lightning should restore the winner's optimizer state through its normal
checkpoint connector. ClanBasedTuning then reapplies the receiving trial's
current optimizer configuration through the Strategy's optimizer-state restore
seam.

This ordering preserves inherited moments while allowing the next generation to
use distinct learning rates, weight decay, momentum, or other explicitly
supported optimizer-side values.

An independently acting learning-rate scheduler usually conflicts with this
ownership model because it resumes changing the same values after Clan evolution
sets them. Initial support should reject such competing schedulers unless a
future integration defines one authoritative combined policy.

### Whole-experiment restoration

Normal winner checkpoint transfer is required for the first functional system.
Whole-Tuner restoration is a separate capability.

Tune can persist experiment metadata after some members have reported at a
synchronous boundary and before the remaining members arrive. Such a snapshot
may describe an incomplete collective round. Ordinary PBT can tolerate this
because its trials are independent; Clan Tuning cannot assume that independently
restoring those trial records reconstructs one coherent generation.

The initial support contract should therefore state that whole-experiment resume
across an interrupted round is unsupported. The hazard must remain documented,
but rollback normalization, shared-checkpoint retention, and durable generation
transactions belong to later recovery work unless an earlier milestone proves
they are required.

## Population and resource authority

### Decision

One Tune trial is one Clan member. Ray's ordinary `TuneConfig.num_samples` is
the initial population input; ClanBasedTuning should not ask the user to provide
a second population size that can disagree with Ray.

The setup must validate the following equality before training begins:

> Ray `num_samples` = generated Tune trials = Clan members = DDP world size = simultaneously resident dedicated devices

Initial support should use Ray's default `BasicVariantGenerator` without grid
expansion or another search algorithm, so `num_samples` remains the actual Clan
population rather than one multiplier in a larger trial-generation scheme. Ray's
generated `total_samples` then provides a defensive confirmation of the same
value after experiment construction.

### Setup boundary

The full-residency check belongs principally at the assembly boundary before
`Tuner.fit()`, where the Tune configuration and cluster allocation are visible
together. The scheduler should retain defensive population checks, but Ray may
stage pending actors independently of the scheduler's preferred trial, so the
scheduler alone cannot guarantee preflight admission.

Initial support should require:

- one device and one Tune resource bundle per member;
- identical per-trial resource topology;
- enough dedicated matching devices for the complete generated population;
- no grid expansion or alternate search algorithm;
- `max_concurrent_trials` equal to `num_samples`;
- actor reuse disabled;
- no external workload consuming the clan's allocation;
- no member queuing or time multiplexing.

The exact public assembly helper belongs to the usability design. It must consume
ordinary Ray and Lightning objects rather than introduce another TuneConfig,
RunConfig, or population schema.

## Data and fitness

Training data remains normally partitioned by Lightning and PyTorch distributed
sampling. Fitness data must be replicated so every member evaluates the same
examples in the same deterministic order.

A custom sampler class is not required. A standard PyTorch
`DistributedSampler` configured as one replica with rank zero can express the
replicated evaluation topology. A thin helper may later remove ceremony without
becoming a second data system.

Fitness must remain member-local until Ray compares trials. Synchronizing the
fitness metric across DDP ranks would erase the differences required for
selection.

The integration must qualify:

- identical validation dataset and transforms;
- identical validation loader length and boundary timing;
- no rank-dependent augmentation or sampling;
- one final fitness value per qualifying validation event;
- no sanity-check or unrelated report triggering evolution.

## PyTorch DDP boundary

PyTorch DDP should own gradient bucketing, all-reduce, and the normal distributed
wrapper lifecycle. ClanBasedTuning must not reimplement collectives.

A focused two-process probe on PyTorch 2.10 showed that native DDP
initialization can synchronize initial parameters and buffers, subsequent buffer
broadcasts can be disabled on the wrapper before training, reduced gradients
remain common, and distinct learning rates then produce divergent parameters.
The probe is useful evidence but is not yet repository-qualified support.

The leading design is therefore to export initial synchronization and structural
verification to native DDP, then prevent forward-time buffer broadcasts that
would erase member divergence. The exact Lightning hook and the stability of the
post-construction setting require a committed framework-contract test before the
manual DDP synchronization code can be rejected conclusively.

The initial DDP qualification should focus on ordinary automatic optimization,
one model replica and device per trial, identical parameter and optimizer
topology, and standard all-reduce. Manual optimization, custom communication
hooks, skipped reductions, SyncBatchNorm, model averaging, and other altered
collective semantics remain unsupported until separately analyzed.

Precision support is not yet an accepted invariant. BF16 is the leading GPU
candidate. FP16 must be decided by a direct divergent-member GradScaler probe;
it should not be rejected or accepted from assumption alone.

## Failure and stopping

### Failure

One active member failure invalidates the current collective. Initial behavior
should fail or stop the complete clan, with no independent member recovery and
no attempt to continue with a smaller world.

Sophisticated rollback and recovery are later capabilities. The initial system
needs clear failure propagation, finite collective timeouts, and useful error
context, not speculative repair machinery.

### Stopping

Per-trial stopping is incompatible with Clan Tuning and should be rejected.
Tune's ordinary trial stop conditions are evaluated per result and can terminate
one trial before the synchronous controller completes a population decision.
Lightning early stopping can create the same mismatch.

Planned completion must be collective and occur at a synchronized population
boundary. The exact public representation of that condition is unresolved. It
may be implemented through the controller or through a coordinated experiment
stopper, but milestone two must choose one owner and avoid a second independent
termination clock.

External cancellation and hard global time budgets may stop the complete clan
without another evolutionary transition. They are operational interruption, not
member-local stopping.

## Framework ownership matrix

| Responsibility | Primary owner | ClanBasedTuning contribution |
| --- | --- | --- |
| Trial identity and configuration | Ray Tune | Require one trial per member; use `num_samples` as population input; restrict mutable fields to optimizer configuration |
| Evaluation cadence | Lightning | Require qualifying synchronized evaluation events; do not duplicate cadence |
| Training and validation loops | Lightning | No replacement loop |
| Gradient reduction | PyTorch DDP | Supply one cross-trial process group and divergence-safe options |
| Training-data partitioning | Lightning/PyTorch | Supply external rank topology; preserve native sampling |
| Fitness-data replication | User data setup/PyTorch | Optional thin helper and validation contract |
| Fitness comparison and parent selection | Ray PBT specialization | Select one winner and target every other member |
| Checkpoint contents | Lightning | Permit member-local save on every Clan rank |
| Checkpoint selection and transfer | Ray PBT | Preserve native exploitation lifecycle |
| Optimizer construction | Lightning/user model | No package-owned optimizer factory |
| Optimizer configuration after restore | ClanBasedTuning | Explicit reconciliation seam after inherited state load |
| Resource declaration | Ray Tune | Validate full-residency invariant at assembly |
| Failure execution | Ray/Lightning/PyTorch | Convert any member failure into collective failure |
| Planned completion | Unresolved collective owner | Must occur only at synchronized population boundary |
| Whole-experiment recovery | Later recovery design | Initially unsupported across interrupted rounds |

## Decisions that survive review

1. One Tune trial is one member.
2. Ray `num_samples` is the initial population input; grid-expanded or alternate
   search populations are not initially supported.
3. Every member is concurrently resident and participates in every training
   gradient.
4. Lightning owns evaluation cadence, including qualified subepoch cadence.
5. One qualifying evaluation/checkpoint report is one PBT decision opportunity.
6. Synchronous PBT is the evolutionary foundation.
7. One deterministic winner supplies the next generation.
8. Ray owns checkpoint selection and transfer; Lightning owns checkpoint
   contents.
9. The receiving trial's optimizer configuration is applied after inherited
   optimizer-state restoration.
10. Training data is partitioned; fitness data is replicated.
11. Per-trial stopping and independent recovery are unsupported.
12. Current proof-of-concept components have no architectural presumption.
13. Whole-experiment recovery across an interrupted round is deferred.

## Unresolved implementation gates

The following questions block support claims but do not invalidate the ownership
model:

1. Which Lightning subepoch validation configurations preserve exact loop and
   data continuation after a Tune pause and checkpoint restore?
2. What is the narrowest supported Lightning seam for member-local checkpoint
   writing on every Clan rank?
3. Does the proposed PBT one-winner override remain correct under three or more
   members, ties, repeated generations, and restore?
4. Where should planned collective completion live without introducing a second
   termination clock?
5. Which assembly surface can validate full dedicated residency before any
   member enters the collective?
6. Which DDP options and precision modes survive direct divergent-member probes?
7. What minimum version-pinned source-contract tests are required for the private
   Ray seam and the Lightning/DDP integration seams?

## Evidence basis

This report is based on the governing roadmap, the pinned dependency ranges in
`pyproject.toml`, upstream source review, and focused local probing. The detailed
claim-to-source mapping is maintained in
[`framework_alignment_evidence.md`](framework_alignment_evidence.md).
