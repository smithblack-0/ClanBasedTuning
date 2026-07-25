# ClanBasedTuning Project Roadmap

Status: governing project roadmap
Date: 2026-07-25

Clan Tuning is a distributed training method that combines shared-gradient
training with online adaptation of optimizer hyperparameters. ClanBasedTuning
is the library project developing that method into functionality that can be
used with PyTorch, Lightning, and Ray Tune.

This roadmap governs the development program from the present proof of concept
through a usable, useful, and industry-capable implementation. It does not
presume that the finished architecture has already been discovered. Detailed
engineering artifacts may resolve framework ownership, component boundaries,
and issue order, but they may not silently change the Clan Tuning mechanism,
the accepted development criteria, state authority, scientific meaning, or
public support claims.

## Technical foundation

The roadmap depends on two pieces of technical background: what Clan Tuning
does, and what the ClanBasedTuning project is trying to make practical. This
section establishes that background without contracting the implementation
architecture that the first milestone must still discover.

### Clan Tuning

Clan Tuning shares training progress across a population while preserving
optimizer-side variation for selection. Its value and limits follow directly
from how that sharing is organized.

#### Why combine DDP and PBT?

Distributed algorithms gain speed by dividing work, but they do not all
parallelize the same part of a problem.

Distributed Data Parallel (DDP) lets several copies of one model process
different training examples and combine their gradients. This accelerates one
shared training trajectory, but every copy ordinarily follows the same
optimizer policy. A useful learning-rate or momentum schedule must therefore
already be known or chosen by some separate process.

Population Based Training (PBT) instead runs several model trajectories under
different hyperparameters. It periodically compares them, continues from
successful members, and mutates their configurations. PBT can discover a
changing optimizer policy during training, but the population pays for
independent trajectories rather than combining their work to accelerate one.

Clan Tuning exchanges most of PBT's trajectory diversity for the ability to do
both at once. Members cooperate to produce a common gradient, as in DDP, but
apply that gradient through different optimizer states and hyperparameters.
They then compete through fitness evaluation. Selection can adapt the optimizer
policy while the whole clan contributes to training progress.

#### A Clan Tuning round

A **clan** is the cooperating population, and each candidate within it is a
**member**. An **optimizer configuration** is the set of optimizer
hyperparameters allowed to vary between members, such as learning rate, weight
decay, or momentum. A **round** is the interval between population decisions.
Completing a round selects the training state from which the clan's next
generation begins.

Each round prepares a common starting point, trains through cooperation, and
ends in competition and selection. In precise terms:

1. The evolution policy produces a perturbed optimizer configuration for each
   member.
2. Identical model parameters and optimizer state are loaded into every member.
   All members begin the round as clones.
3. Each member's perturbed optimizer configuration is applied to its copied
   optimizer state.
4. For every training batch in the round:

   * Each member computes gradients from its own batch of training data.
   * The clan pools those gradients into one common gradient.
   * Each member applies the common gradient through its own optimizer, using
     its own optimizer state and configuration. This gradually causes the
     members to diverge.
5. Every member is evaluated on the same held-out data and assigned a fitness
   score.
6. The fittest member's model parameters, optimizer state, and optimizer
   configuration become the sole basis for the clan's next generation.

#### Consequences and tradeoffs

This construction makes Clan Tuning a greedy, online optimizer scheduler. It
can adapt learning rate, weight decay, momentum, or other optimizer-side choices
along the training trajectory rather than requiring their complete schedule in
advance.

Tradeoffs accepted in this exchange include:

* It can tune optimizer hyperparameters, but not model, data, or other choices
  that would already have affected the shared gradient.
* It is slower than a DDP run supplied with a perfect optimizer schedule.
* It gives up most of PBT's model diversity and follows the basin selected at
  each round.
* Rounds must be frequent enough that the pooled gradient remains useful to the
  diverging member trajectories that apply it.

The project aims to make the cost of finding a strong optimizer policy small
enough that many ordinary distributed jobs no longer need a manually prescribed
optimizer schedule. Achievable speed, useful round frequency, optimizer-policy
quality, and scientific value remain matters for direct experimentation rather
than promises implied by the mechanism.

### ClanBasedTuning under development

ClanBasedTuning is the library project intended to make Clan Tuning practical
for developers who already work with distributed PyTorch, Lightning, or
PBT-like systems. The intended result must serve both an ordinary user who
wants a short setup and a sophisticated integrator who needs inspectable,
composable Clan-specific capabilities.

PyTorch, Lightning, and Ray Tune form the target framework context for the
current program. They already provide much of the training, distribution,
optimization, trial, checkpoint, and scheduling machinery that a solution may
need. ClanBasedTuning should add only the behavior required by Clan Tuning,
while preserving useful framework ownership and extension points.

Exactly where those responsibilities belong is not yet a finished-product
contract. Determining the most native implementation, the necessary
Clan-specific invariants, and the proper public boundaries is the work of
framework-alignment research. Later milestones then turn those findings into an
evolutionary controller, integratable orchestration, a usable ordinary path,
general optimizer utility, and industry-ready capability.

## Development contract

The roadmap needs stable criteria for judging the work even while the
implementation architecture remains open. These criteria define what counts;
milestone exit evidence later determines whether a particular stage has
delivered it.

### What counts

Good ClanBasedTuning development advances the following qualities together:

* **Algorithmic fidelity.** The implementation preserves the cooperation,
  competition, optimizer-only variation, and single-parent generation
  transition that define Clan Tuning.
* **Framework-native alignment.** The project uses native lifecycle owners and
  extension points where they fit, introducing custom machinery only for a
  demonstrated Clan-specific gap.
* **Coherent responsibility.** Components have inspectable, composable
  responsibilities. Convenience may assemble them, but it must not conceal a
  second training system or make advanced use depend on private internals.
* **Practical usability.** The ordinary path eventually removes distributed
  setup work that a user should not have to reconstruct, without taking the
  user's model or training decisions away from the frameworks that own them.
* **Optimizer utility.** Configuration application grows beyond a toy
  one-optimizer case into an explicit, predictable system for realistic
  optimizers and parameter groups.
* **Industry relevance.** The mature system is observable, diagnosable,
  documented, and qualified for serious distributed workloads, including
  model-sharded training.
* **Scientific relevance.** Examples use the actual public implementation and
  increasingly exercise workloads capable of illustrating Clan Tuning's real
  potential. The project values interpretable evidence, not demonstrations
  engineered to guarantee a favorable result.

These qualities constrain one another. Framework minimalism cannot excuse an
unusable common path; convenience cannot excuse hidden ownership; passing tests
cannot by itself establish scientific value; and an interesting experiment
cannot excuse an unauditable implementation.

### Continuous obligations

Documentation is a critical development product at every milestone, not a
release-stage cleanup task. Research findings, accepted invariants, design
choices, public contracts, examples, diagnostics, limitations, and user
guidance must develop alongside the capability they explain.

Tests and direct evidence are equally continuous. Each implemented
responsibility requires focused tests; each integration claim requires
integration evidence at the relevant framework and hardware boundary; and each
support claim must remain no broader than the configurations actually
qualified. Tests show that a stated contract is met. They do not replace the
reasoned choice of the contract or the human review of framework evidence.

Examples and scientific work use the same evolving public implementation.
Early examples may establish mechanics; later examples should become more
realistic and scientifically informative as the system gains capability. The
project must not maintain a cleaner private research implementation beside the
library users receive.

Changes to algorithmic meaning, state authority, recovery, public support, or
scientific interpretation remain explicit project decisions. Ordinary design
improvements are expected during implementation, but must remain visible in
the relevant research, design, gate, code, test, and documentation artifacts.

## Development method

The current strategy begins with framework research because the correct
Clan-specific contracts cannot be designed independently of the native
Lightning, Ray Tune, and PyTorch lifecycles through which they must operate.
This is a development strategy for the present uncertainty, not a claim that
framework research is itself part of the finished product.

Relevant framework documentation, source, examples, and focused probes are
reviewed through auditable research tracks. Those tracks preserve what was
considered, the evidence found, the alternatives weighed, and the resulting
conclusions for human review. Accepted invariants are then extracted into
concise gate files that later designs and implementations must satisfy. The
research record explains why; the gate files state what subsequent work must
not violate.

Design artifacts translate those accepted constraints into concrete component
boundaries, integration points, ordering, state authority, and verification
plans. Implementation, tests, documentation, and examples then develop
together. When new evidence invalidates a boundary or assumption, the design
and its gates are corrected rather than protected by compensating machinery.

## Roadmap

The milestones below express capability dependencies, not calendar estimates.
Only the active milestone should be decomposed into issue-level work. Later
milestones state the result, major boundary, and evidence expected without
pretending their detailed designs are already settled.

Live project position belongs in [`STATUS.md`](../STATUS.md). This roadmap does
not track the current branch, active PR, or day-to-day completion state.

### Cumulative milestones

Every milestone must satisfy the continuous documentation, test, evidence, and
example obligations above. A milestone is not complete merely because its
central code path runs.

#### 1. Completion of framework-alignment research

**Outcome.** The project has an accepted, evidence-backed basis for designing
ClanBasedTuning in a framework-native manner.

**Work.** Relevant Lightning, Ray Tune, and PyTorch lifecycles, ownership
boundaries, extension points, and failure behavior are investigated. Research
documents state the conclusions. Audit tracks record the framework resources
considered, the evidence extracted, and the alternatives weighed in a form
suitable for human review. Accepted invariants are separated into concise gate
files. One or more engineering plans translate those invariants into an
actionable implementation route.

**Exit.** Human review has accepted the research conclusions needed for the
next milestone. The audit tracks are complete enough to inspect the reasoning;
the invariant gate files cover the relevant algorithm, lifecycle, state,
failure, and ownership constraints; unresolved questions are either answered
or explicitly retained as blockers; and the implementation plan can be audited
against those gates.

#### 2. Evolutionary subsystem

**Outcome.** ClanBasedTuning has an independently invokable evolutionary
controller that expresses the population-decision side of Clan Tuning.

**Work.** The controller is designed, implemented, tested, and documented as a
framework-independent population policy. It consumes ordinary data describing
one complete population, compares fitness, selects the sole winning member, and
produces the next optimizer-hyperparameter configurations.

Its engineering documentation explains lifecycle boundaries, input and output
data structures, algorithms, state, and failure behavior. A reproducible pet
loop demonstrates several synthetic generations and shows where an external
training system supplies fitness and consumes the decision.

The controller does not import Ray trial objects, choose a Tune scheduler hook,
transfer checkpoints, construct optimizers, apply live optimizer values, or own
training and distributed execution.

**Exit.** Focused and plain-data compatibility tests pass; intentional state and
failure ordering are exercised; the controller is independently invokable
through its accepted contract; engineering documentation agrees with the
implementation; and the repeated synthetic example makes the evolutionary
transition inspectable.

#### 3. Integratable orchestration subsystems

**Outcome.** The evolutionary controller and Clan-specific training primitives
can be manually composed into a real distributed Lightning workflow in which
Clan Tuning works end to end.

**Work.** Direct Ray evidence is used to choose the narrowest invocation path
that gathers one complete population for the accepted controller and executes
its decision through native trial lifecycle. The design may compare a scheduler
specialization with a thin adapter, but it preserves one policy authority and
native Ray ownership of trial execution, checkpoint/configuration assignment,
pause/resume, resources, and scheduler lifecycle.

The workflow is formally analyzed for integration points and opportunities.
Small primitives needed to hook Clan behavior into the Lightning lifecycle are
implemented. A working multi-rank training example manually composes those
primitives with the required external Lightning, PyTorch DDP, model-wrapping,
and distributed-data configuration.

Package-managed DDP setup, model wrapping, and data partitioning are deliberately
outside this milestone. Their absence makes the system awkward to use, not
theoretically unintegratable; removing that external ceremony is the next
milestone's job.

**Exit.** The selected Ray seam passes direct framework-contract tests. The
manual composition completes multiple rounds, uses independent training batches
and the same held-out evaluation data, produces shared gradients and member
divergence, selects a sole parent, inherits state through native framework
behavior, and continues from the next generation. Failure boundaries and the
manual reader path are documented.

#### 4. Usability

**Outcome.** A Lightning user can attach ClanBasedTuning through a short,
documented construction path without manually assembling the surrounding DDP,
model, and data lifecycle.

**Work.** Distributed-data wrapping, DDP hooks, component-construction
factories, and the focused optimizer-configuration applier needed by the simple
path are developed. A manufacturing frontend returns the concrete Lightning
plugins required by the caller rather than a second factory or package-owned
trainer. Attaching those plugins configures the intended DDP model behavior and
distributed training data correctly.

The ideal user pipeline is designed explicitly before the frontend is fixed.
The user guide is developed with that path, and the examples include a simple
complete use of the construction function alongside the lower-level manual
composition.

**Exit.** The simple construction path and its direct primitives pass tests;
the resulting Lightning job configures DDP and data loading as documented; the
user guide is coherent and sufficient for a new user; the simple example runs
through the supported round lifecycle; and the convenience layer remains
auditable composition rather than a parallel implementation.

#### 5. Utility

**Outcome.** ClanBasedTuning can apply evolved optimizer configurations
predictably across realistic optimizer, parameter-group, and multi-optimizer
layouts.

**Work.** The `OptimizerAdapter` system is implemented and documented. By
default, it copies configuration entries into same-named optimizer
hyperparameters. More specific filters may target an optimizer type, optimizer
instance or reference, parameter group, and remapping dictionary. When several
filters match, the most specific applicable rule wins through a deterministic,
documented ordering.

The system remains explicit about which configuration values are applied and
where. It must not silently ignore a declared value or reinterpret the user's
complete experiment configuration as a package-owned schema.

**Exit.** Unit and integration tests cover default mapping, remapping,
specificity, ambiguity and failure behavior, multiple optimizers, and
specialized parameter groups. Reference documentation explains the resolution
model, and examples demonstrate both multi-optimizer and parameter-group use in
real Clan Tuning workflows.

#### 6. Industry

**Outcome.** ClanBasedTuning is usable for serious industry workloads within a
clearly declared and directly qualified support envelope.

**Work.** The project develops production-quality logging, observability,
diagnostics, and failure guidance; clean support for Fully Sharded Data
Parallel (FSDP); and support for other selected Lightning-native model-sharding
technologies where direct need and framework evidence justify it. An explicit
industry-readiness audit or qualification checklist tests the complete
operational path rather than treating model sharding alone as proof of
readiness.

Industry work builds on the same public controller, orchestration primitives,
construction path, and optimizer utility. It does not introduce a separate
enterprise implementation. Documentation covers deployment assumptions,
supported framework and hardware boundaries, restoration and diagnosis, and
the operational meaning of emitted records.

**Exit.** The declared logging and diagnostic contracts work under the
supported distributed configurations; FSDP and any other claimed sharding
technology pass direct accelerator, checkpoint, restoration, and failure
tests; the readiness audit passes for the stated envelope; and documentation
and scaled examples are sufficient for an independent engineering team to run,
inspect, and troubleshoot the system.

## Project success

The project succeeds as an engineering program when Clan Tuning is faithfully
implemented through framework-native, inspectable responsibilities; users can
adopt it through both a practical ordinary path and composable primitives; its
optimizer policy can address realistic training systems; and serious
distributed users can run, observe, restore, and diagnose it within an honest
support boundary.

Scientific examples are part of reaching that result, not a final ceremony
after the software is declared complete. As the milestones advance, examples
should progress from inspecting the evolutionary mechanism, through a working
manual distributed composition, to usable optimizer studies and scaled
workloads. They should use the public package and make the method's behavior,
costs, limitations, and potential interpretable.

The roadmap can require those examples to be real, reproducible, and
scientifically meaningful. It cannot contract favorable findings or guarantee
that a particular experiment will establish importance. Scientific judgment
depends on the evidence the completed system makes possible; engineering
acceptance depends on whether the system and its claims are correct,
inspectable, usable, and adequately supported.
