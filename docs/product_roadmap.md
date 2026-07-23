# Product thesis and roadmap

Status: governing product direction
Date: 2026-07-22

This document defines why ClanBasedTuning exists, how it will be developed,
what it intends to support, and how that support will be introduced. Technical
plans may choose implementations within these boundaries; they may not redefine
the product.

## Project thesis

Population Based Tuning (PBT) can adapt an optimizer during training, but its
population members normally train independently. Clan Tuning instead gives the
population a shared reduced gradient while retaining separate optimizer states
and configurations. Distributed workers can therefore compare and evolve
optimizer behavior while continuing to contribute to one gradient signal.

ClanBasedTuning will make this method usable in existing PBT and distributed-
training systems. It is not a new trainer, tuning framework, or experiment
frontend. It supplies the Clan-specific behavior that those systems lack, then
returns control to them.

The product has one implementation at two levels:

- documented primitives for developers building their own integration; and
- thin utilities that assemble those primitives for common workloads.

The primitives are the product foundation. The utilities reduce setup; they do
not create a second system.

## Clan Tuning

In a conventional distributed job, workers reduce gradients and apply the same
optimizer policy. In conventional PBT, population members apply different
policies but train independently. Clan Tuning combines these operations:

1. Each member computes gradients on its training data.
2. The clan reduces those gradients.
3. Each member applies the shared gradient through its own optimizer state and
   configuration.
4. Members are evaluated on comparable data.
5. PBT selects successful members, transfers training state, and mutates the
   optimizer configuration.
6. The receiving member applies its current configuration after inherited
   optimizer state is restored.

This makes Clan Tuning a greedy online optimizer scheduler. It can adapt
learning rate, weight decay, momentum terms, and other behavior applied after
gradient reduction.

The method is deliberately narrower than general hyperparameter tuning. Model,
data, and other choices that affect gradients before reduction cannot be
isolated through member fitness after those gradients are shared. Clan Tuning
also does not establish a globally optimal schedule: results remain conditional
on the population, mutation policy, evaluation signal, and observed training
path.

Members must use compatible model and optimizer structures when state is
transferred. They must also reach collective and selection boundaries
compatibly; a failed participant can affect the active clan.

## Product definition

ClanBasedTuning will provide the coordination, lifecycle integration,
configuration application, diagnostics, and records needed to implement the
sequence above. Ray Tune, Lightning, and PyTorch form the first supported
composition because they already own the surrounding PBT, training, and
collective operations.

Those frameworks remain authoritative. ClanBasedTuning does not own model or
optimizer construction, the training loop, PBT selection and mutation,
checkpoint transport, general restoration, gradient reduction, or experiment
configuration. It owns only the Clan-specific requirements at their boundaries.

A Ray trial represents a population member in the reference composition. That
mapping does not define the algorithm: member, trial, worker, process, rank, and
device remain distinct concepts. Preserving that distinction allows later
support for sharded or multi-worker members without requiring the initial
release to implement them.

## Governing principles

Development begins with ownership. Each component must identify a missing
Clan-specific responsibility, expose the smallest useful contract for it, and
leave the surrounding lifecycle with its established framework. Public
primitives establish these contracts; convenience utilities only compose them.
Documentation and examples are part of each contract because an extension
point that cannot be understood or applied independently is not a usable
primitive.

| Principle | Commitment |
|---|---|
| Minimal ownership | Implement only the Clan-specific behavior absent from the surrounding frameworks. Custom framework machinery requires a documented gap. |
| Primitives first | Put essential behavior behind focused public contracts that can be used outside the reference composition. |
| Thin convenience | Assemble the same primitives for common cases without adding a training loop, configuration language, recovery system, or hidden execution model. |
| Framework-native integration | Preserve native objects, lifecycles, configuration, and failure authority wherever the framework can perform the work. |
| Explicit control | Keep the user's scheduler, trainer, model, optimizers, and tuning configuration visible. Apply optimizer configuration through an explicit extension point. |
| One implementation | Use the released primitives in convenience utilities, examples, and scientific studies. Do not maintain a second research or turnkey implementation. |
| Deliberate extensibility | Avoid assumptions that unnecessarily bind a member to one process, rank, or device; add new topologies only when their contracts are understood. |
| Continuous usability | Deliver contract tests, diagnostics, examples, and documentation with the capability they describe. Public class and concept documentation uses a concise business-technical register: purpose, ownership, lifecycle, limits, and extension points before internal mechanics. |

Operational theory and library ownership remain separate throughout the
project. The algorithm defines what must happen; it does not assign every step
to this package.

## Product intent and support

The project intends to support common PBT users and developers building bespoke
pipelines through the same primitives. Support expands by workload complexity:
the initial path is made dependable before the contracts take on broader
optimizer and execution layouts.

| Workload | Product response | Status |
|---|---|---|
| Simple Ray Tune, Lightning, and PyTorch workload | Add Clan Tuning through a short, recognizable integration while retaining the existing training function and framework objects | Initial commitment |
| Bespoke pipeline using the same frameworks | Assemble the required Clan-specific primitives directly | Initial commitment; examples expand with the primitive set |
| Multiple optimizers, parameter-group policies, or renamed configuration fields | Apply one trial configuration to the intended optimizer targets through a reusable mapping contract | Planned expansion |
| Analysis or reuse of the selected optimizer behavior | Inspect member lineage and optimizer changes; replay a selected policy without rerunning population search | Product intent; replay follows a stable history contract |
| Scientific use | Run maintained studies and publication configurations against the released package | Continuous product intent; formal reference follows product validation |
| FSDP, multi-worker members, multi-node clans, elasticity, or asynchronous populations | Preserve Clan semantics under a new execution topology | Candidate expansion |

The initial simple workload means synchronous PBT, one Lightning process and
GPU per member on a single node, Lightning automatic optimization, PyTorch DDP
gradient reduction, one optimizer with one parameter group, matching-name
configuration application, compatible model and optimizer structures, and FP32
or BF16 training. Broader APIs do not imply support beyond this envelope.

General non-optimizer hyperparameter tuning is outside the product definition.
The later execution topologies in the table are not initial support claims.

## Delivery difficulty

The main engineering work lies at framework boundaries, where ordinary
assumptions conflict with Clan Tuning.

| Boundary | Required result |
|---|---|
| Trial isolation and shared gradients | Establish clan membership and rendezvous across otherwise independent trials, then use PyTorch collectives rather than replacing them. |
| Replica synchronization and member divergence | Share gradients without allowing initialization or buffer synchronization to erase intentional model differences. |
| Exploitation and restoration | Let Ray and Lightning move and restore state, then apply the receiving member's current optimizer configuration in the correct lifecycle phase. |
| Fitness comparison | Evaluate members on comparable data without reducing away the differences PBT must select. |
| Failure behavior | Detect and report Clan context without inventing independent recovery that conflicts with framework authority or strands peers. |
| Optimizer variation | Begin with the simple path, then extend configuration application without turning the user's experiment configuration into a package-owned schema. |

These boundaries determine the order of implementation and evidence. They do
not prescribe the classes or hooks used to satisfy them.

## Success conditions

ClanBasedTuning becomes a supported product when:

- a PBT and distributed-training user can install it, adapt a conventional
  workload, complete and restore a run, inspect the result, and diagnose
  supported failures from public documentation;
- a bespoke integration can use the same public primitives without depending
  on private convenience behavior;
- each integration point has one stated Clan-specific responsibility, an
  explicit owner on either side, and direct contract and failure evidence;
- support claims name the tested framework versions, topology, precision, and
  lifecycle behavior;
- class, concept, integration, and troubleshooting documentation explain why a
  component exists, what it owns, how it participates in the lifecycle, and
  where its support ends; and
- maintained scientific work imports the public package rather than carrying a
  second implementation.

An end-to-end demonstration establishes only the behavior it exercises, not the
complete support contract.

## Current position

The repository contains a two-process CPU contract probe and a native Ray PBT
exploit-and-restart cycle. Together they exercise separate trials forming a DDP
clan, training, checkpoint inheritance, post-restore configuration application,
and collective reformation.

This is a proof of concept, not the initial supported product. The public
primitive surface, GPU path, support evidence, documentation, packaging,
optimizer-adaptation breadth, history, and replay remain incomplete.

## Rollout

Each stage produces a usable increment and retires the risks needed by the next
stage. Dates and issue-level designs belong in the active technical plan.

| Stage | User-visible result | Exit condition |
|---|---|---|
| **1. Primitive foundation — current** | Developers can understand and use the Clan-specific lifecycle pieces directly. | Each retained primitive has one public purpose and owner, contract and failure tests, concise class documentation, and a direct example. The reference composition is expressible through these primitives alone. |
| **2. Simple reference alpha** | A PBT user can run Clan Tuning on the declared single-node GPU workload through thin Ray Tune and Lightning setup utilities. | The documented path completes training, evaluation, exploitation, restoration, and continued training in its published compatibility envelope, including supported failure diagnostics. |
| **3. Integration beta** | Researchers and infrastructure engineers can evaluate the package as a dependency and apply it to more varied optimizer layouts. | Public APIs and history formats are stable for the supported envelope; optimizer configuration supports the declared mixed layouts; packaging, compatibility records, upgrade policy, examples, diagnostics, and performance characterization are complete. Replay enters this stage only through the established history and configuration contracts. |
| **4. Scientific reference and 1.0** | Users can cite one released implementation and reproduce the evidence used to evaluate Clan Tuning. | Maintained public-package experiments characterize behavior, overhead, and relevant baselines; every stated claim maps to published configuration and artifacts; the exercised API and support envelope are ready for 1.0 commitment. |
| **5. Evidence-driven expansion** | Additional optimizer or execution workloads become supported under the same product principles. | Each addition has a defined user situation, framework owner, lifecycle and failure contract, compatibility claim, documentation path, and automated evidence. FSDP is the first execution-topology candidate. |

Only the active stage is decomposed into implementation work. Later stages state
direction and exit conditions; evidence from earlier stages determines their
detailed design.

## Roadmap control

- The active technical plan traces work to a governing principle and stage exit
  condition.
- Product intent, support boundaries, and release outcomes belong here.
  Implementation choices and unresolved class or hook decisions belong in the
  technical plan.
- A capability is supported only when its contract, documentation, diagnostics,
  compatibility statement, and evidence agree.
- Changes to the algorithm's meaning, package ownership, support envelope, or
  release outcomes require a roadmap revision.
- Review this roadmap when a stage exits or evidence invalidates a product
  assumption.
