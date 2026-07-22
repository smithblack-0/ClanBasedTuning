# Product direction and roadmap

Status: consolidated product-model draft

Last updated: 2026-07-22

This revision is ready for review of the product direction, supported-use
boundaries, and rollout logic. It is not a final roadmap or a certification of
the current implementation. Capability statuses, documentation work, and deeper
engineering concerns are preliminary inputs for the architecture audit and will
change when evidence changes.

Feedback is requested on four questions:

1. Does the consolidated model describe the product we are trying to build?
2. Are the use cases distinct, worthwhile, and supported at the right levels?
3. Do the success conditions follow from that model without mixing in feature
   design?
4. Does the rollout deepen the model in the right order?

Line editing, detailed feature commitments, and judgments about the current
architecture are not the review target for this revision.

## Consolidated product model

ClanBasedTuning should make evolutionary optimizer adaptation over shared
distributed gradients usable through existing training and tuning frameworks.
The novelty is not merely that DDP and evolution can be combined. The intended
contribution is a robust set of CBT primitives, one complete integration for a
common use case, and reproducible evidence for the algorithm and the additional
capabilities developed here.

The package should be as native as possible so it can leverage existing,
robustly tested subsystems. PyTorch should remain responsible for distributed
tensor operations, Lightning for training orchestration, and Ray for population
scheduling and trial lifecycle. ClanBasedTuning should add the CBT-specific
behavior and the hooks or overrides required to express it. The contracts must
make authority and ordering explicit without creating a second implementation
of a framework-owned paradigm.

Viability therefore means **narrow but complete, and extensible without being
speculative**. The project should thoroughly support a deliberately simple,
useful configuration. Users whose systems differ in known ways should have
documented extension points or focused components to adopt. More demanding
topologies should remain possible to investigate, but the package should not
claim or prematurely abstract support that has not been designed and tested.

The runtime product and the research product are related but distinct. The
runtime supplies the public implementation and contracts. Reference experiments
consume that public implementation to establish fidelity, characterize its
engineering behavior, and support the new publication. The experiments must not
contain a hidden second implementation of CBT.

This produces three primary product units:

1. **Supported integration:** one end-to-end Ray, Lightning, and PyTorch path
   that an ordinary user can install and apply without designing distributed
   lifecycle machinery.
2. **Adoptable components:** focused CBT primitives and contracts for users who
   already have bespoke training or tuning infrastructure.
3. **Reference implementation:** maintained experiments and technical
   documentation that make the algorithm, framework integration, and
   publication claims inspectable and reproducible.

Professional engineering quality applies to all three. The code should be
written on the assumption that it will be reviewed, copied, and used to learn
how to implement CBT; reference quality is part of the product, not a polishing
stage after the features work.

## Intended use and support levels

Support is defined by use case, not by whether the user is an individual, a
small lab, or a large organization. The same organization may use the package at
several levels.

| Use case | Concrete configuration or need | Intended support |
|---|---|---|
| Simple optimizer adaptation | Each model and its training state fit on one device; one optimizer with one parameter group; compatible member topology; fixed, fully resident synchronous population; ordinary Lightning automatic optimization; Ray synchronous PBT | Complete supported path, initially on one GPU node |
| Customized optimizer adaptation | The supported topology is retained, but optimizer mapping requires multiple groups, aliases, tuple-valued settings, transformations, or another explicit reconciliation policy | Supported through a documented optimizer hook and tested examples; not configuration inference |
| Bespoke system integration | An engineer needs selected CBT strategy, coordination, or optimizer-adaptation behavior inside an existing system rather than the complete Ray-Lightning path | Documented component contracts and reference use; operational support limited to declared compositions |
| Scientific replication | A researcher needs to reproduce established CBT behavior and evaluate the additional claims of this project | Maintained reference experiments using the public package |
| Advanced distributed adoption | A model needs multiple devices, sharding, multi-node membership, elasticity, asynchronous populations, or other production-specific behavior | Not part of the initial support promise; preserve plausible extension paths and add support only from evidence |

The first release is viable only if the simple optimizer-adaptation path is
complete and useful. The customized and component paths prevent that narrow
entry point from becoming the definition of CBT. They do not promise that every
possible composition is already supported.

## Success conditions

The following conditions turn the product model into release gates. They are
independent: a working training run cannot compensate for an unclear contract,
weak documentation, or an unsubstantiated scientific claim.

| Condition | What must be true | Reason |
|---|---|---|
| Framework-native implementation | Framework-owned mechanisms remain implemented by PyTorch, Lightning, Ray, or another established dependency; CBT code contains only its algorithmic delta and necessary integration hooks | Native reuse gives users one engineering truth and the benefit of mature framework testing and maintenance |
| Complete simple path | The declared one-device-per-member, one-optimizer configuration installs, trains, exploits, checkpoints, restores, reports fitness, and fails intelligibly on a supported single-node GPU environment | A proof of concept becomes useful only when its common path is complete rather than selectively demonstrated |
| Explicit cross-framework contracts | Authority, ordering, invariants, and unsupported combinations are clear at checkpoint, exploitation, restart, failure, topology, optimizer, metric, and data boundaries | The frameworks may own the behavior, but CBT must state what their composition requires |
| Adoptable component boundaries | Advanced users can identify and use focused CBT behavior without accepting a package-owned Trainer, tuning frontend, distributed runtime, or configuration language | Existing systems usually need an improvement to their own pipeline, not a replacement framework |
| Honest compatibility envelope | Supported framework versions, platforms, precision modes, optimizer layouts, and topologies are specific and backed by automated or reproducible evidence | Narrow verified support is more useful than broad ambiguous compatibility claims |
| Reference-quality engineering | Public interfaces, source structure, documentation, tests, diagnostics, compatibility discipline, and release practice are suitable for code expected to be audited and copied | The implementation itself is part of the contribution and must earn long-term trust |
| Publishable evidence | Public-package experiments establish prior-algorithm fidelity, measure overhead and scaling in the supported envelope, and demonstrate clearly stated additional capabilities | Robust software enables the research contribution but does not replace scientific evidence |

The framework-native condition is a design gate rather than a product
description. Any custom scheduler control, checkpoint manager, distributed
runtime, recovery system, or training loop is presumptively wrong until a
specific framework gap and the required CBT behavior are demonstrated. A
subclass or plugin is not automatically native if its body reimplements the
paradigm it extends.

## Preliminary capability view

These tables organize what must eventually be tracked. They are not support
claims. **Observed** means that a current test or example exercises a behavior;
it does not mean the design has passed the framework-native audit.

### Supported integration

| Capability | Present evidence | Next decision or evidence |
|---|---|---|
| Shared gradients with divergent optimizer application | Observed in a two-process CPU Lightning probe | Audit the strategy against current Lightning and PyTorch extension contracts |
| Native Ray exploitation and member restart | Observed in a CPU Ray/PBT lifecycle test | Audit every Ray override and private dependency; verify complete job restoration separately |
| Simple optimizer adaptation | A one-optimizer, one-group adapter exists | Define the exact initial optimizer fields and optimizers; test construction and post-restore reconciliation |
| Single-node GPU execution | No current evidence | Verify the complete supported path with NCCL and the selected precision modes |
| Comparable member fitness | A replicated evaluation sampler and local metric convention exist | Check ordinary Lightning data-module, sampler, validation, and metric compositions |
| Checkpoint, restart, and failure composition | One exploit/restore cycle is observed | State framework authority and ordering, then add restoration and failure-injection coverage for the supported path |
| Diagnostics and compatibility | Partial README guidance and pinned dependencies exist | Define required user-visible context and publish an evidence-linked compatibility matrix |

### Components and extension paths

| Capability | Present evidence | Next decision or evidence |
|---|---|---|
| Optimizer reconciliation hook | Callable injection is implemented and unit tested | Decide whether its current timing and inputs form a sufficient public contract for realistic custom layouts |
| Lightning strategy and environment | Public concrete objects are returned by the factory | Determine whether each override is the smallest native hook and whether Ray details leak into reusable contracts |
| Ray scheduler and rendezvous | Native trials retain Ray identity and lifecycle in the current design | Determine whether coordination is a focused CBT policy adapter or an alternate lifecycle controller |
| Independent component adoption | Components are importable but only the complete composition is demonstrated | Identify supported standalone compositions from real use cases; do not invent generic interfaces during the audit |
| Future topology growth | One process, device, and member are currently equivalent | Determine which contracts merely restrict the first adapter and which unnecessarily encode that equivalence into the conceptual core |

### Reference implementation and research

| Capability | Present evidence | Next decision or evidence |
|---|---|---|
| Algorithm fidelity | Mechanism-level CPU tests exist | Define which established CBT results or behaviors must be reproduced |
| Additional research contribution | Not yet consolidated | Write a claims-and-evidence matrix before selecting experiments |
| Performance characterization | No current evidence | Measure overhead, throughput, memory, and scaling only after the supported architecture is settled |
| Reproducible experiment package | One illustrative CPU example exists | Build maintained configurations, outputs, interpretation, and environment records around the public API |

## Preliminary documentation plan

Documentation should follow the same consolidated-to-detailed structure as the
product. The exact file layout is not committed, but the user questions are
already distinguishable.

| Documentation unit | Question it answers | Primary use case |
|---|---|---|
| Overview and decision guide | What problem does CBT solve, when should I use it, and what is actually supported? | All users |
| Supported-path quick start | How do I run the simple one-optimizer configuration correctly? | Simple optimizer adaptation |
| Concepts and framework contracts | How do shared gradients, divergent optimizer state, PBT, checkpoints, fitness, and framework authority fit together? | Direct users and reviewers |
| Support and compatibility matrix | Which versions, devices, precision modes, optimizers, topologies, and lifecycle features are verified? | Adopters and operators |
| Extension guide | How do I customize optimizer reconciliation or consume a focused component without bypassing its invariants? | Customized and bespoke integration |
| Troubleshooting and diagnostics | What does a hang or lifecycle failure mean, what context should I inspect, and which framework owns recovery? | Operators |
| Reproduction guide | How do I reproduce each fidelity or publication result from the public package? | Scientific replication |
| Maintainer and upstream notes | Which upstream contracts are relied upon, how are compatibility changes detected, and what belongs upstream? | Maintainers and framework reviewers |

The current README, build contract, source ledger, probes, and example are source
material for these documents. Their existence does not establish that this user
journey is complete, and historical documents must be clearly separated from
live contracts after the audit.

## Deeper concerns for the architecture audit

These are unresolved questions, not accepted defects or planned features. They
are recorded now because a favorable answer is necessary before the current
proof of concept can be treated as the product nucleus.

| Concern | Why it may matter | Audit question |
|---|---|---|
| Member/process/device equivalence | The current topology may make multi-device members or hierarchical groups difficult later | Is the equivalence confined to the first Ray-Lightning adapter, or embedded in lower-level CBT contracts? |
| Ray lifecycle coupling | The implementation relies on native PBT behavior and some private lifecycle seams | Are the overrides minimal and sentinel-tested, and should any missing public hook be proposed upstream? |
| Scheduler versus scientific scope | Ray can mutate arbitrary config values, while current CBT gradients may justify only optimizer adaptation | Does the public API distinguish technically accepted configuration from scientifically supported mutation? |
| Optimizer mutation semantics | Construction, checkpoint restoration, scheduler state, precision scaling, and mutation can establish competing authorities | Is there one explicit ordering contract that delegates each operation to its framework owner? |
| Data and fitness comparison | Distributed sampler and metric defaults assume equivalent replicas, while CBT intentionally preserves member differences | Can normal Lightning data and metric facilities express the required comparison without package-owned alternatives? |
| Collective failure behavior | One member stopping or retrying independently can strand peers in collectives | Which Ray failure and restart modes naturally satisfy the CBT contract, and what must merely be rejected or documented? |
| Precision and compiled execution | AMP scalers, BF16/FP16, compilation, and communication hooks can alter optimizer or synchronization ordering | Which modes compose through native hooks, and which require separate evidence or deferral? |
| Component boundaries | Concrete objects are public, but importability alone does not make them independently useful | What are the smallest real adoption units, and what context do their contracts require? |
| Documentation authority | Historical plans and ledgers describe superseded designs beside the live contract | Which artifacts remain evidence, which are authoritative, and which should be archived or rewritten? |

The audit should search current framework designs before preserving any custom
machinery. Its output should classify existing units as retain, strengthen,
redesign, remove, or defer and explain the framework evidence behind the call.

## Rollout roadmap

The stages are evidence gates rather than calendar promises. Later stages stay
coarse until earlier work resolves their architecture.

### 0. Product consolidation — current

Agree on the product model, use-case support levels, success conditions, and the
questions the architecture audit must answer.

Exit condition: this document is accepted as a sound direction for the next
pass. Preliminary capability rows and feature details may still change.

### 1. Framework-native architecture audit

Trace the current implementation and its framework dependencies end to end.
Resolve ownership, duplication, extension-point choice, topology assumptions,
public component boundaries, and stale documentation before extending the
feature set.

Exit condition: an evidence-backed architecture disposition and an issue-sized
correction plan, with major design decisions returned for review before
implementation.

### 2. Supported single-node path

Apply the audit corrections and make the declared simple optimizer-adaptation
configuration complete on a supported GPU environment. Add the contract tests,
compatibility evidence, diagnostics, packaging, and task-oriented documentation
required by that path.

Exit condition: a user inside the declared support envelope can install, adapt,
run, restore, understand, and troubleshoot a useful experiment without reading
the source or designing lifecycle machinery.

### 3. Component and research release

Stabilize the component contracts justified by real adoption cases. Build the
reference experiments, fidelity evidence, performance characterization, and
additional publication evidence on the public supported package.

Exit condition: each public component has a defined adoption contract, and each
publication claim maps to a reproducible artifact and result.

### 4. Evidence-driven expansion

Consider broader optimizer layouts, multi-node execution, multi-device members,
sharded strategies, alternative population policies, or production-specific
operation only when a concrete use case and the preceding evidence justify the
work.

Exit condition: any promoted capability has a defined use case, framework
owner, contract, compatibility claim, documentation path, and automated or
reproducible evidence. No item in this stage is part of the initial release
commitment.

## Tracking policy

This document is the consolidated product and rollout view. Component contracts
define detailed behavior; tests, examples, compatibility records, benchmarks,
and experiments supply evidence.

- Only the active stage should be decomposed into GitHub issues. Later stages
  remain planning inputs until prior evidence determines their shape.
- Each active issue should identify the supported use case, affected contract,
  framework owner, acceptance evidence, and roadmap row it advances.
- Observed behavior does not advance to supported behavior until its design,
  documentation, compatibility envelope, and required evidence agree.
- Scope changes that alter scientific meaning, framework authority, recovery,
  or the public support promise require review before implementation.
- At every stage exit, reread this document from the consolidated model downward.
  A deeper item that cannot be traced to the model is misplaced, premature, or
  evidence that the model itself needs revision.

The only active engineering issue before this draft is accepted should remain
the framework-native architecture audit. Detailed correction issues should come
from its evidence rather than from guesses made during product planning.
