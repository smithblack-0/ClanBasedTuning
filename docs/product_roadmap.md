# Product roadmap

Status: live product and maturity tracker

Last updated: 2026-07-22

This document defines what ClanBasedTuning is trying to become, who the first
supported product is for, and what evidence is required before its maturity
claims advance. It is intentionally a small next step. It does not certify the
current architecture, replace component contracts, or commit the project to
every possible distributed-training use case.

## Product outcome

ClanBasedTuning aims to be a publishable, professionally engineered collection
of composable primitives for evolutionary optimizer adaptation over shared
distributed gradients, with:

- one thoroughly supported Ray Tune and Lightning integration for ordinary
  users;
- focused components and explicit contracts for engineers integrating CBT into
  bespoke systems; and
- reproducible experiments establishing scientific fidelity and the additional
  capabilities of this implementation.

The package should improve an existing training system rather than replace it.
PyTorch remains authoritative for distributed tensor operations, Lightning for
training orchestration, and Ray for population scheduling and trial lifecycle.
ClanBasedTuning owns the novel CBT behavior and the minimum hooks, adapters, or
overrides required to express it.

Custom code that recreates a framework-owned paradigm is a viability failure
unless a documented framework gap makes it necessary. An extension point alone
does not make an implementation native: every override must delegate the
surrounding mechanism to its framework and contain only the CBT-specific delta.

## Audience and intended promise

| Audience | Intended capability | Initial promise |
|---|---|---|
| Individual Lightning and Ray user | Add optimizer evolution to an existing, conventional training function | Turnkey supported path |
| Small research lab | Run repeatable GPU studies with documented lifecycle contracts, diagnostics, and reproducible examples | Turnkey supported path |
| Research or infrastructure engineer | Adopt the useful strategy, coordination, optimizer-reconciliation, or lifecycle pieces without accepting a replacement training framework | Stable, documented component contracts |
| Scientific replicator | Reproduce established CBT behavior and the publication's additional claims from complete experiment configurations | Maintained reference experiments |
| Large lab or commercial organization | Audit the design and integrate selected components into bespoke infrastructure | Credible foundation, not initial turnkey production support |

The first release is successful for the first two audiences. Component adopters
and replicators are first-class secondary audiences. Large organizations should
not be structurally walled off, but multi-node scale, operational guarantees,
and production support are claims that require later evidence.

## Viability gates

These gates apply independently. Passing a technical integration test does not
substitute for the other gates.

| Gate | Success condition | Why it matters |
|---|---|---|
| Framework authority | Ray, Lightning, and PyTorch remain the sole engineering truths for the paradigms they own; CBT adds only necessary policy and hooks | Reimplementing mature machinery creates conflicting authorities and makes adoption unjustifiably risky |
| Contract clarity | Checkpoint, framework, exploitation, restart, failure, topology, data, metric, and optimizer authority are explicit across framework boundaries | Framework-owned behavior can be safe only when the integration requirements and ordering are auditable |
| Common-path usability | A declared single-node GPU configuration can be installed, attached to a conventional Lightning/Ray workload, run, restored, and understood from public documentation | The package must be usable rather than merely demonstrative |
| Component adoption | Sophisticated users can use focused CBT capabilities without importing a package-owned Trainer, tuning frontend, or configuration language | Bespoke systems need components, not another framework |
| Compatibility | Supported versions, precision modes, optimizers, schedulers, and topology combinations are narrow, explicit, and covered by evidence | Honest support boundaries are more valuable than broad untested claims |
| Operational clarity | Diagnostics identify membership, rendezvous, exploit/restore, and collective failures without duplicating framework observability | Distributed failures must be diagnosable by the intended user |
| Scientific evidence | Reference experiments establish fidelity, characterize overhead, and demonstrate the additional publishable capabilities | Engineering quality supports the contribution but does not replace its research claims |
| Maintainer quality | Public API, documentation, tests, release process, and upstream compatibility discipline meet the standard expected of a serious Lightning extension | Viability includes long-term trust, not only current correctness |

## Capability and maturity tracker

Status meanings:

- **Demonstrated:** exercised by a current automated contract or complete
  reference path.
- **Provisional:** implemented, but its public contract or support evidence is
  incomplete.
- **Unverified:** desired for the initial supported product but not yet proven.
- **Deferred:** outside the initial release promise; reconsider only with a
  concrete use case and contract.

| Area | Intended initial capability | Current status | Evidence or next gate |
|---|---|---|---|
| Shared-gradient CBT core | Common reduced gradients with member-specific optimizer application | Demonstrated on CPU | Two-process Lightning contract probe |
| Ray exploitation lifecycle | Native synchronous PBT selection, mutation, checkpoint cloning, and member restart | Demonstrated on CPU | Native Ray exploit/restore contract test |
| Framework ownership | Thin native integration with no duplicated lifecycle paradigm | Provisional | Whole-system framework-native audit; classify every custom owner and override |
| Single-node GPU | One resident member per GPU using native DDP/NCCL | Unverified | End-to-end GPU contract and workload example |
| Common optimizer tuning | Thoroughly support ordinary learning-rate, weight-decay, and selected optimizer-state mutations | Provisional | Define the supported subset; verify representative optimizers and restore ordering |
| Custom optimizer layouts | Caller-supplied reconciliation for bespoke optimizer/group structures | Provisional | Audit the callable contract and document tested extension examples |
| Checkpoint and restart | Ray and Lightning retain authority while CBT requirements and restore ordering remain explicit | Provisional | Verify full job restoration, including `Tuner.restore()`, and document authority/failure contracts |
| Failure behavior | Collective-safe failure and framework-owned recovery for declared configurations | Unverified | Failure-injection tests and a decision on the first supported recovery subset |
| Fitness and data | Comparable member-local fitness without erasing model differences | Provisional | Audit sampler/metric integration against normal Lightning data patterns |
| Precision | FP32 and BF16 on the supported GPU path | Unverified | GPU numerical and lifecycle contracts; FP16 remains separate until scaler semantics are resolved |
| Diagnostics | Actionable population, rendezvous, exploit, restore, and collective context | Unverified | Define required user-facing signals and reuse framework logging surfaces |
| Compatibility | Explicit tested Ray, Lightning, PyTorch, Python, and platform matrix | Provisional | Convert dependency pins and CI coverage into a published compatibility table |
| User documentation | Install, quick start, concepts, extension guide, troubleshooting, and limitations | Provisional | README, contract, and CPU example exist; complete the user journey after the audit |
| Scientific replication | Reproduce established CBT behavior and additional publication claims | Unverified | Define the claims/evidence matrix, then build complete reference experiments |
| Multi-node and advanced strategies | Evidence-driven support for larger or sharded topologies | Deferred | Reconsider after the supported single-node product and topology audit |

## Rollout roadmap

The stages are evidence gates, not calendar promises.

### 0. Seed and product recentering — current

The repository contains a working CPU vertical slice and lifecycle tests. This
roadmap supplies the previously missing product success condition and maturity
language.

Exit condition: the intended audiences, viability rules, and next audit target
are explicit. This stage does **not** assert that the current implementation has
good architectural bones.

### 1. Framework-native architecture audit — next

Audit the complete implementation against current Ray, Lightning, and PyTorch
designs. For every custom component and override, determine:

1. the unique CBT requirement;
2. the framework that owns the surrounding paradigm;
3. the intended extension point;
4. whether the code is the smallest necessary hook or a competing
   implementation; and
5. whether its current contract preserves plausible component adoption and
   future topologies.

Classify each unit as retain, strengthen, redesign, remove, or defer. Reconcile
or clearly archive stale engineering documents as part of the same pass.

Exit condition: an evidence-backed architecture decision and issue-sized
correction plan, with no major ownership question hidden inside feature work.

### 2. Supported single-node alpha

Implement the corrections from the audit, then complete the primary user path:
single-node GPU execution, the selected optimizer/precision subset,
framework-owned checkpoint and recovery contracts, diagnostics, compatibility
coverage, packaging, and task-oriented documentation.

Exit condition: an individual or small lab in the declared support envelope can
install the package, adapt an ordinary Lightning/Ray workload, complete and
restore a useful run, diagnose failures, and understand every important support
boundary without reading the implementation.

### 3. Publishable research release

Add reproducible fidelity experiments, overhead and scaling characterization,
and experiments for the additional capabilities claimed by the new work. The
scientific harness must consume the public package rather than contain a hidden
second implementation.

Exit condition: each publication claim maps to a reproducible artifact and
result, while the documented product path satisfies the supported-alpha gates.

### 4. Evidence-driven beta expansion

Consider multi-node execution, multi-device members, additional optimizers,
advanced Lightning strategies, alternative population policies, or new backend
adapters only when a concrete user path and the prior evidence justify them.

Exit condition: each promoted capability has an explicit audience, framework
owner, contract, compatibility claim, and automated evidence. This stage is not
part of the initial release commitment.

## Tracking policy

This file is the single summary of product maturity and rollout order. Detailed
behavior belongs in component contracts; completed evidence belongs in tests,
examples, benchmarks, and experiment artifacts.

- Only the active stage is decomposed into GitHub issues. Later stages remain
  roadmap entries until earlier evidence determines their correct shape.
- Every active issue should name its audience, contract or capability changed,
  success evidence, and affected maturity row.
- A maturity row advances only when its linked evidence exists. Implementation
  alone is not sufficient.
- New feature proposals must identify the existing framework owner and justify
  every custom hook or override before implementation.
- Scope expansion that changes audience, scientific meaning, ownership, or
  recovery is discussed before it enters the active stage.
- The roadmap is reviewed whenever a stage exits or an audit invalidates a
  product assumption.

The immediate next issue set should be created from the Stage 1 audit findings,
not guessed in advance.
