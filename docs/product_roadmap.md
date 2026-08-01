# ClanBasedTuning Project Roadmap

Status: governing project roadmap
Date: 2026-07-25  
Revised: 2026-07-31 — milestone and document-system assumptions removed; product meaning retained.

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
architecture that engineering work must still discover.

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

Exactly where those responsibilities belong is not a finished-product
contract. Direct framework evidence, behavioral contracts, and design work
resolve the necessary Clan-specific invariants and public boundaries while
leaving replaceable implementation choices open.

## Development contract

The roadmap needs stable criteria for judging the work even while the
implementation architecture remains open. Implementation and qualification
evidence determine whether the project actually delivers them.

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

Documentation is a critical development product throughout the program, not a
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
improvements are expected during implementation, but must remain visible in the
artifacts that own the affected behavior or claim.

## Development direction

Development first establishes and directly qualifies a complete framework-native
implementation of Clan Tuning. Later capabilities must extend that same public system
rather than replace it with separate convenience, research, or production
implementations.

Current sequencing, acceptance boundaries, and implementation choices belong in the
active contracts, designs, plan, and qualification records rather than this roadmap.
Live project position belongs in [`STATUS.md`](../STATUS.md); this roadmap does not track
the current branch, active pull request, or day-to-day work queue.

## Project success

The project succeeds as an engineering program when Clan Tuning is faithfully
implemented through framework-native, inspectable responsibilities; users can
adopt it through both a practical ordinary path and composable primitives; its
optimizer policy can address realistic training systems; and serious
distributed users can run, observe, restore, and diagnose it within an honest
support boundary.

Scientific examples are part of reaching that result, not a final ceremony
after the software is declared complete. As the implementation and its
extensions advance, examples should progress from inspecting the evolutionary
mechanism, through a working manual distributed composition, to usable optimizer
studies and scaled workloads. They should use the public package and make the
method's behavior, costs, limitations, and potential interpretable.

The roadmap can require those examples to be real, reproducible, and
scientifically meaningful. It cannot contract favorable findings or guarantee
that a particular experiment will establish importance. Scientific judgment
depends on the evidence the completed system makes possible; engineering
acceptance depends on whether the system and its claims are correct,
inspectable, usable, and adequately supported.
