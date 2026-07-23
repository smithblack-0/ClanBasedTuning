# Product direction and roadmap

Status: governing product direction

Date: 2026-07-22

ClanBasedTuning will make Clan Tuning usable as a framework-native optimizer
scheduling system. It combines the cooperative gradient computation of
Distributed Data Parallel (DDP) training with the runtime adaptation of
Population Based Training (PBT): members share one gradient signal, apply it
through different optimizer configurations, and periodically inherit the most
successful training state.

The project is for researchers and machine-learning engineers who already use
distributed training and want to explore optimizer behavior during a run
without training a fully independent model for every population member. The
initial product will integrate Ray Tune, Lightning, and PyTorch; the method and
its public primitives remain distinct from that first framework composition.

This roadmap defines what the project is building, the support it intends to
earn, the evidence required, and the order in which the product becomes usable.
Implementation plans may choose classes and hooks within these boundaries; they
may not redefine the algorithm, framework ownership, or release outcomes.

## Clan Tuning

Clan Tuning is easiest to understand through the two systems it combines.

In a DDP-style job, workers hold replicas of the same model, reduce gradients,
and apply the same optimizer policy. Their cooperation advances one training
trajectory efficiently, but the optimizer schedule is normally fixed in
advance.

In adaptive PBT, population members train independent model trajectories under
different policies. Periodic evaluation allows stronger members to replace
weaker ones and mutate their configurations, but the population pays for
independent training.

Clan Tuning keeps DDP's cooperation while introducing PBT-style adaptation. One
round proceeds as follows:

1. Members begin from the same inherited model and optimizer state, with
   different optimizer configurations.
2. Each member computes gradients from its current parameters on an independent
   training batch.
3. The clan pools those gradients into one update shared by every member.
4. Each member applies the pooled gradient through its own optimizer state and
   configuration, allowing the model trajectories to diverge.
5. At the round boundary, members are evaluated on the same data.
6. The most successful member becomes the exclusive parent of the next
   generation.
7. The next generation starts from that member's training state with optimizer
   mutations applied across the clan.

The central idea is that cooperation and evolution do not require the same
state to remain shared. The clan cooperatively produces a common resource—the
pooled gradient—then tests different ways of applying it. Fitness selects the
optimizer behavior that used that resource most effectively.

### Value and limits

Clan Tuning can adapt learning rate, weight decay, momentum terms, and other
optimizer behavior applied after gradient reduction. Within that domain it may
remove the need to choose a complete optimizer schedule before training, while
using the whole population's gradients to advance each member.

This is not general hyperparameter tuning. A model, data, or training choice
that changes gradients before they are pooled cannot be isolated through
member fitness afterward. Batch size, architecture, augmentation policy, and
similar choices are therefore outside the method unless a later formulation
changes where members diverge.

Exploration also has an unavoidable cost. A hypothetical DDP run with the
perfect optimizer schedule is better by construction because it spends no work
testing inferior alternatives. Clan Tuning is valuable only when the cost of
finding a useful schedule during training is lower than the cost or loss
associated with choosing one in advance. Whether that cost is slight, and for
which workloads, is an empirical question rather than a product promise.

Selection is greedy, not globally optimal. Results remain conditional on the
population, mutation policy, evaluation signal, round length, and training path.
The pooled gradients must also remain useful across the diverging member states;
if the members cease to produce mutually intelligible updates, the method loses
its training advantage.

### Precedent

The method is not starting from a blank technical premise.
[Hyperparameter-Divergent Ensemble Training (HDET)](https://arxiv.org/abs/2604.24708)
demonstrates that distributed replicas can explore different learning rates
during one large-model training run and use their relative performance to adapt
the schedule. HDET uses fan-out phases followed by parameter averaging, whereas
Clan Tuning pools gradients throughout a round and selects one parent state.
The paper therefore supports the broader feasibility of hyperparameter-divergent
distributed training without establishing Clan Tuning's specific algorithm or
performance claims.

## The product

ClanBasedTuning will provide the coordination, lifecycle integration,
configuration application, diagnostics, and records needed to run the algorithm
inside established training systems. It is not a Trainer, tuning framework, or
experiment frontend.

The first reference composition uses:

- Ray Tune for trials, scheduling, mutation, pause and resume, checkpoint
  transport, and experiment state;
- Lightning for the training and validation lifecycle, optimizer construction,
  precision, callbacks, and checkpoint serialization and restoration; and
- PyTorch DDP for process-group communication, gradient bucketing, and gradient
  reduction.

ClanBasedTuning supplies only the missing Clan-specific behavior: membership and
rendezvous across trials, intentional-divergence safeguards, the exclusive
parent transition, comparable fitness, and application of the receiving
member's optimizer configuration after inherited state is restored.

For the common path, a user will supply `ClanBasedTraining` as the Ray Tune
scheduler and call `make_clan_lightning_plugins()` inside the existing training
function. The helper returns the concrete Lightning Strategy and callbacks; the
user's model, `Trainer`, Tune configuration, optimizer construction, and run
configuration remain visible.

The same implementation is exposed at two levels:

- focused public primitives for developers building or modifying an
  integration; and
- thin utilities that assemble those primitives for the supported
  Ray-Lightning-PyTorch workload.

The primitives are the foundation. Convenience utilities may remove setup, but
they may not introduce a second training loop, configuration language,
checkpoint system, recovery policy, or hidden execution model.

## Development contract

The library earns breadth by establishing focused contracts, not by stretching
one convenience path until it appears generic. Each custom component must own a
real Clan-specific gap and leave the surrounding lifecycle with its established
framework.

| Principle | Project commitment |
|---|---|
| Minimal ownership | Implement only behavior required by Clan Tuning that the surrounding frameworks do not already provide. |
| Framework-native integration | Preserve the user's native model, Trainer, scheduler, configuration, callbacks, checkpoints, and failure authority wherever their frameworks can remain responsible. |
| Public primitives | Put essential behavior behind focused contracts usable outside the reference composition. |
| One implementation | Build convenience utilities, examples, and scientific studies from the same primitives. |
| Explicit control | Keep optimizer configuration application and other consequential extension points visible to the user. |
| Evidence-gated support | Support a workload only when its contract, diagnostics, documentation, compatibility claim, and automated evidence agree. |
| Deliberate extensibility | Separate member, trial, process, rank, and device concepts so the initial topology does not become the algorithm. |
| Efficient documentation | Explain purpose, mechanism, ownership, lifecycle, limits, and extension points at the layer where the reader needs them. |

These commitments apply to low-level code as strongly as to the common path. A
primitive that cannot be understood, tested, or used independently is not yet a
product primitive.

## Intended support

Support expands first by workload complexity, then by execution topology. The
initial path must become dependable before the package takes responsibility for
general optimizer layouts or distributed systems whose member boundaries differ
from the reference composition.

| Workload or capability | Product response | Status |
|---|---|---|
| Simple Ray Tune, Lightning, and PyTorch workload | Add Clan Tuning through a short, recognizable integration while retaining the user's training function and framework objects | Initial commitment |
| Bespoke pipeline using the same frameworks | Assemble the documented Clan-specific primitives directly | Initial commitment; examples expand with the primitive set |
| Multiple optimizers, parameter-group policies, renamed fields, or structured values | Apply one trial configuration to the intended optimizer targets through a reusable mapping contract | Planned integration-beta capability |
| Optimizer history and selected-policy reuse | Inspect member lineage and optimizer changes; replay a chosen policy without rerunning population search | Product intent after the history contract stabilizes |
| Maintained scientific studies | Evaluate the method through versioned experiments that import the released package | Continuous intent; formal reference follows product validation |
| FSDP, multi-worker members, multi-node clans, elasticity, or asynchronous populations | Preserve Clan semantics under a separately designed execution contract | Candidate expansion, not an initial commitment |

The initial simple workload is synchronous and single-node. Each member is one
Ray trial, Lightning process, GPU, DDP rank, and complete model. Lightning uses
automatic optimization with one optimizer and one parameter group; Ray varies
matching-name optimizer fields; training uses FP32 or BF16; and every member
must be resident for the complete round. Broader public interfaces do not imply
support beyond this envelope.

General non-optimizer hyperparameter tuning remains outside the product
definition. Later optimizer layouts expand how post-reduction behavior is
targeted; later execution topologies change how a logical member is represented.
Those are separate development axes.

## Engineering work that determines viability

The algorithm is simple to state, but it crosses framework boundaries whose
ordinary assumptions conflict with intentional member divergence.

| Boundary | Required result |
|---|---|
| Trial isolation and shared gradients | Form one process group across otherwise independent Ray trials, then let PyTorch perform ordinary DDP reduction. |
| Initialization and divergence | Start a generation from common inherited state without allowing DDP initialization or buffer broadcasts to erase later member differences. |
| Exclusive parent selection | Reuse Ray's synchronous PBT checkpoint and trial lifecycle while replacing its normal upper/lower-quantile selection with one parent for the complete next generation. |
| Optimizer authority | Restore the selected member's optimizer state first, then apply the receiving member's current optimizer values without creating a second tuning schema. |
| Comparable fitness | Evaluate the same examples on every member without synchronizing away the metric differences selection requires. |
| Failure behavior | Stop a broken collective, preserve the last authoritative framework state, and provide Clan context without inventing independent member recovery. |
| Primitive and convenience parity | Ensure the common helper composes the documented primitives rather than becoming the only path that actually works. |

These boundaries determine implementation order. Exact classes and framework
hooks belong in the active technical plan; the required outcomes belong here.

## Definition of support

A demonstration shows that one path can run. Product support requires more:

- a user in the declared envelope can install the package, adapt a familiar
  workload, complete and restore a run, inspect the result, and diagnose
  supported failures from public documentation;
- the convenience path and direct primitive path execute the same contracts;
- every integration point has one stated Clan-specific responsibility and an
  explicit owner on either side;
- support claims name the tested framework versions, topology, precision, and
  lifecycle behavior;
- failure and restore tests establish authority in the order events actually
  occur; and
- maintained experiments use the released package rather than a separate
  research implementation.

Class, concept, integration, and troubleshooting documentation are part of this
definition. Public behavior is not supported if a user must read private source
or reconstruct the lifecycle from examples.

## Current position

The repository contains useful proof, but not the accepted product.

The two-process CPU probe shows that independent Lightning processes can receive
the same DDP-reduced gradient and diverge after applying different learning
rates. The native Ray probe exercises cross-trial rendezvous, checkpoint
inheritance, target-configuration reapplication, and process-group reformation.
Together they establish the principal framework seams.

They do not yet establish the complete algorithm. The current scheduler retains
Ray's stock quantile selection, while the accepted Clan transition uses one
exclusive parent for the next generation. The current public Lightning classes
also depend on Ray-private runtime records, so the advertised primitive path is
not yet genuinely independent of the convenience composition.

| State | What it means now |
|---|---|
| Demonstrated | Shared reduced gradients, divergent optimizer application, concrete Lightning plugin construction, member-local checkpoint creation, exploit-style restore, and one native Ray transition on CPU |
| Must be corrected | Exclusive-parent generation policy, public primitive boundaries, and optimizer-only variation contract |
| Must be certified | Multi-round lifecycle, single-node GPU behavior, FP32/BF16, SGD/AdamW state restoration, whole-experiment restore, diagnostics, packaging, and user documentation |
| Planned after the simple path | General optimizer mapping, stable history, replay, and wider examples |
| Candidate only | FSDP and other member topologies, multi-node clans, elasticity, and asynchronous execution |

This status is intentionally asymmetric: the package has evidence that the
cross-framework mechanism can work, but it has not yet earned a supported
release.

## Rollout

The stages are cumulative. Each produces a usable increment and retires the
risks needed by the next stage. Only the active stage is decomposed into
implementation issues; later stages remain outcome-level until earlier evidence
settles their design.

| Stage | User-visible result | Exit condition |
|---|---|---|
| **1. Correct algorithm and primitive foundation — current** | Developers can inspect and use the actual Clan-specific pieces, and the reference path implements the accepted one-parent algorithm. | Exclusive selection, optimizer-only variation, rendezvous, DDP divergence, restoration ordering, comparable fitness, and checkpoint ownership have focused contracts and CPU evidence. Public Lightning primitives no longer require private Ray types, and the convenience helper returns the concrete objects built from them. |
| **2. Simple reference alpha** | A PBT user can add Clan Tuning to the declared single-node GPU workload without designing the cross-framework lifecycle. | The documented path completes multiple rounds, exploitation, restoration, continued training, and whole-experiment resume on the pinned FP32/BF16 matrix with supported diagnostics. |
| **3. Integration beta** | Researchers and infrastructure engineers can evaluate the package as a dependency and apply it to broader optimizer layouts. | Public APIs and history formats are stable; the reusable optimizer mapping contract, lineage, compatibility records, upgrade policy, examples, performance characterization, and packaging are complete. Replay enters only through the established history contract. |
| **4. Scientific reference and 1.0** | Users can cite one released implementation and reproduce the evidence used to evaluate Clan Tuning. | Maintained public-package experiments compare algorithm fidelity, ordinary training, full PBT, and CBT with common accounting. Every scientific claim maps to published configuration and artifacts, and the exercised API is ready for 1.0 commitment. |
| **5. Evidence-driven expansion** | Additional optimizer or execution workloads become supported under the same product principles. | Each addition has a concrete user situation, framework owner, lifecycle and failure contract, compatibility claim, documentation path, and automated evidence. FSDP is the first execution-topology candidate. |

The immediate work is therefore not feature expansion. It is to correct the
generation policy, separate the primitives from the Ray convenience path,
finish the multi-round lifecycle, and make the simple GPU composition
supportable. General optimizer mapping and new distributed topologies follow
only after that foundation is real.

## Roadmap control

- The active technical plan traces work to a roadmap stage and exit condition.
- Product purpose, algorithm, intended support, and release outcomes belong
  here. Class design, framework hooks, and unresolved implementation choices
  belong in the technical plan.
- Current evidence is promoted to support only when code, tests, diagnostics,
  documentation, and compatibility statements agree.
- Changes to the algorithm, framework ownership, initial support envelope, or
  release outcomes require a roadmap revision.
- Review this roadmap when a stage exits or evidence invalidates a product
  assumption.
