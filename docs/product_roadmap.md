# Product thesis and roadmap

Status: governing product direction

Date: 2026-07-22

This document defines the intent under which ClanBasedTuning is designed and
reviewed. The principles are project commitments, not optional preferences. If
an implementation conflicts with them, the implementation changes unless the
project deliberately revises this thesis.

## Project thesis

ClanBasedTuning will let developers who already understand Population Based
Training and distributed training use Clan Tuning to adapt optimizers during a
training run. They should be able to add the required Clan Tuning hooks to an
existing pipeline without surrendering that pipeline to a new training
framework.

The product is a small set of well-contracted Clan Tuning primitives. Thin
utilities assemble those primitives for common framework combinations. The
primitives receive at least the same engineering attention as the convenient
path because they are what make the library adaptable, auditable, and useful
beyond its first reference integration.

Operationally, Clan Tuning requires population members to retain distinct
model trajectories, optimizer state, and tuning configuration while
contributing to shared gradients. Each member applies the shared gradient
through its own optimizer. Population selection may transfer training state
between members; the receiving member's current configuration must then be
applied to the inherited optimizer state. Fitness must remain comparable
without reducing away the member differences being selected.

That is the behavior the library exists to enable. It is not a claim that the
library owns the surrounding training topology, scheduler, training loop,
optimizer, gradient reducer, or checkpoint system.

## Governing commitments

| Principle | Project commitment | Design consequence |
|---|---|---|
| Own only the Clan Tuning gap | Existing frameworks remain authoritative for training, population scheduling, distributed computation, optimization, and persistence. ClanBasedTuning implements only behavior and coordination that those owners do not provide. | Every custom component must identify the missing Clan Tuning requirement it owns and delegate the surrounding lifecycle. Reimplementing a framework-owned paradigm is a design failure. |
| Build the primitives as the product | Coordination, optimizer-configuration application, lifecycle integration, and other Clan-specific capabilities will have narrow public contracts and be usable when a caller assembles its own pipeline. | The project will not bury essential behavior inside one turnkey integration or treat lower-level APIs as unsupported implementation debris. |
| Keep convenience thin | Common-case utilities will compose the public primitives, supply sensible defaults, and remove repetitive wiring. They will not create a second execution model. | The convenient path and a custom pipeline use the same behavior. A helper that introduces its own training loop, configuration language, recovery system, or hidden policy is rejected or decomposed. |
| Separate operational theory from library ownership | Documentation and APIs will distinguish what Clan Tuning requires from how a supported framework composition realizes it and from what this package owns. | Terms such as member, trial, worker, process, rank, and device are related explicitly rather than treated as synonyms. A framework mapping cannot silently become an algorithmic restriction. |
| Preserve explicit user control | The user's scheduler, trainer, model, optimizer, configuration, and framework objects remain visible. Configuration is applied to live optimizers through an explicit, extensible operation. | Defaults may cover matching optimizer fields, while mappings may specialize by optimizer type and parameter group. The library will not reinterpret the user's complete experiment configuration as its own schema. |
| Preserve extension paths without speculative systems | Contracts will avoid unnecessary assumptions that prevent a member from containing several workers or a later integration from using model sharding. | The initial release may support a narrow topology, but core identities and interfaces will not equate one member with one process or device. FSDP and other topologies are added only after their lifecycle is designed and tested. |
| Make contracts teachable and auditable | Quickstarts will serve the common path; integration and primitive documentation will explain ownership, ordering, invariants, extension, and failure behavior. Theory will be presented separately from package responsibility. | A common user can start quickly, while a sophisticated user can build a pipeline without reverse-engineering the convenience layer. Documentation quality is part of feature completeness. |
| Maintain one scientific implementation | Scientific examples and publication experiments will consume the released library rather than reproduce Clan Tuning inside a research harness. | Research use can exercise and validate the product without making experiment management a responsibility of the core package. |

These commitments are cumulative. Usability does not justify broad ownership;
minimal ownership does not justify an incomplete common path; a working common
path does not justify weak primitives.

## Support targets

Support is stated in terms of what a user is trying to do. The initial release
contains one primitive system and convenience utilities over it, not separate
basic and advanced implementations.

| User situation | Product target | Initial commitment |
|---|---|---|
| Add Clan Tuning to a conventional PBT and distributed-training job | Keep the existing training function and framework configuration, add the Clan-specific hooks, and run a complete population lifecycle | A thoroughly tested Ray Tune, Lightning, and PyTorch reference composition with thin setup utilities and an end-to-end quickstart |
| Apply a changing configuration across ordinary or mixed optimizer layouts | Explicitly apply the current configuration to the relevant optimizers and parameter groups, including renamed fields and different rules for different groups | A reusable optimizer adapter with useful matching defaults and more-specific mappings by optimizer type and parameter group |
| Integrate Clan Tuning into a pipeline that does not match the reference composition | Select and assemble the necessary Clan-specific capabilities while retaining the pipeline's existing owners | Public primitive contracts, direct usage examples, and tests that do not require adoption of a package-owned trainer or tuning frontend |
| Understand, evaluate, or extend the implementation | Trace operational theory into concrete framework roles, ownership boundaries, lifecycle ordering, and evidence | Layered documentation: concepts, quickstart, integration guide, primitive reference, failure guidance, and worked examples |
| Use the package for research | Build repeatable studies and inspect tuning behavior using the same public implementation users install | Maintained scientific examples and, once claims are fixed, reproducible publication configurations and artifacts |
| Run sharded, multi-node, elastic, asynchronous, or otherwise advanced topologies | Preserve member isolation and Clan relationships under a different execution lifecycle | Not promised in the initial release. Candidate capabilities begin with an explicit topology, owner, contract, and verification plan; FSDP is a priority candidate after the reference path is sound. |

The first reference composition will use trials as the primary member-isolation
boundary. This lets scheduling and checkpoint lifecycle remain with the tuning
framework and leaves room for one member to contain several workers later. It
does not define a population member as a Ray trial in the primitives or in the
theory.

## Where the work is difficult

The central engineering challenge is not exposing more configuration or
connecting three APIs. It is expressing Clan Tuning while owning as little of
the host system as possible.

| Difficulty | Required outcome |
|---|---|
| Members must share gradients across boundaries that a tuning system normally treats as independent trials | Establish the required communication relationship without replacing the tuning or distributed framework |
| Distributed trainers ordinarily assume replicas should remain identical, while Clan Tuning requires member trajectories to diverge | Reuse native gradient reduction while preventing unrelated synchronization from erasing intentional state |
| Exploitation combines inherited training state with the receiving member's current configuration | Make restore authority and configuration-application order explicit without taking over framework checkpointing |
| Real pipelines use multiple optimizer types, parameter groups, aliases, and structured fields | Provide a clear configuration-application primitive that scales by composition rather than a growing special-case function |
| Fitness must be comparable and member-local at the same time | Coordinate data and reporting so selection is meaningful without synchronizing away the signal |
| A failed participant can invalidate a live collective | Define failure and recovery contracts that cooperate with the host frameworks instead of inventing a competing controller |
| A later member may span several workers or shards | Keep logical member identity separate from trials, processes, ranks, and devices from the beginning |

The project will spend engineering effort on these boundaries even when the
visible code is small. A thin library is the result of resolved ownership, not
an excuse to leave lifecycle behavior implicit.

## Definition of success

The product has fulfilled this thesis when all of the following are true:

- A developer familiar with PBT and DDP can add Clan Tuning to the supported
  reference pipeline, understand the few additional hooks, complete training,
  exploitation, restoration, and evaluation, and diagnose failures from the
  documentation.
- The convenience layer is demonstrably orchestration over public primitives;
  it contains no alternative implementation of their behavior.
- A sophisticated user can understand and assemble the primitives without
  adopting the reference integration or reading its private internals.
- Optimizer configuration remains explicit and supports realistic differences
  among optimizer types and parameter groups without imposing a package-wide
  experiment schema.
- Each custom integration point has one stated responsibility, an explicit
  framework owner on either side, contract tests, and documented failure
  behavior.
- The implementation and documentation never confuse the theory's population
  model with the current framework mapping.
- Scientific examples and results use the public package, and support claims
  are limited to configurations backed by direct evidence.

A successful demonstration is evidence toward these outcomes. It is not a
substitute for them.

## Rollout

The rollout builds outward from the governing commitments. Later stages remain
directional until evidence from the active stage fixes their detailed design.

### 1. Reconcile the proof of concept with the thesis

Audit every current component and lifecycle seam. Retain, redesign, or remove it
according to the ownership and primitive-first commitments. Resolve the core
primitive inventory, optimizer-application model, framework authority, and the
relationship between logical members and the initial trial-based composition.

Exit: every retained custom unit has a unique Clan-specific responsibility; the
common path is expressible entirely by composing the proposed primitives; and
no unresolved product decision is disguised as an implementation detail.

### 2. Establish the primitive foundation

Implement and document the accepted primitives for coordination, intentional
divergence, optimizer configuration, exploit/restore integration, comparable
fitness, and contract failures. Test them at their own boundaries before relying
on the complete reference pipeline as proof.

Exit: each primitive has a stable purpose, explicit ownership and ordering,
direct examples, contract and failure tests, and no duplicated framework
machinery.

### 3. Complete the supported reference composition

Build the Ray Tune, Lightning, and PyTorch path as thin orchestration over the
same primitives. Complete an ordinary single-node GPU lifecycle, including
training, evaluation, exploitation, restoration, diagnostics, and experiment
recovery. Provide the quickstart and realistic optimizer-mapping examples.

Exit: a user in the declared support envelope can add Clan Tuning to a familiar
job and be operational without designing the cross-framework lifecycle, while
the resulting code remains recognizably their Ray, Lightning, and PyTorch
pipeline.

### 4. Release a reference-quality library

Stabilize public APIs, packaging, compatibility evidence, diagnostics,
documentation, and examples. Perform a fresh system review for duplicated
ownership, convenience-layer drift, and accidental topology assumptions.

Exit: the common path and primitive path both satisfy the definition of success
on the published compatibility matrix, and the package is suitable for users to
inspect, extend, and cite.

### 5. Establish the scientific release

Define the claims and comparison plan, then run maintained experiments through
the released package. Separate reproduction of established Clan Tuning behavior
from evidence for new claims, and publish the configurations, accounting,
artifacts, and results needed to interpret both.

Exit: every scientific claim maps to a reproducible public-package experiment;
the research harness contains no second Clan Tuning implementation.

### 6. Expand from demonstrated need

Consider FSDP, multi-device members, multi-node execution, additional tuning
systems, asynchronous populations, and other topologies individually. Expansion
begins only after the user situation, host-framework owners, member topology,
lifecycle contract, and verification method are concrete.

Exit: each added capability preserves the governing commitments and carries an
honest, evidence-backed support boundary. No capability is admitted merely
because the initial interfaces can be stretched to contain it.
