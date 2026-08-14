# Active implementation plan

Status: current implementation sequence

## Authority

This plan sequences present work. It does not change the governing
[roadmap](product_roadmap.md), [system behavior](contracts/system_behavior.md),
[population invariants](contracts/population_resolution_invariants.md), or public API
contract in [`api.md`](api.md).

## Current baseline

The first complete single-node CPU function path is implemented through Ray Tune,
Lightning, and PyTorch. The productization pass has normalized the ordinary user path to
framework-native extension points:

- ordinary Ray function trainable, with no CBT trainable wrapper;
- `ClanScheduler` through `TuneConfig.scheduler`;
- metric and mode through `TuneConfig`;
- one Ray trial/resource allocation per Clan member;
- `ClanDDPStrategy` through Lightning's strategy interface;
- `ClanTuneReportCallback` through Lightning's callback interface; and
- plain nested dictionaries for mutation configuration.

The public example exposes userspace optimizer application inline instead of hiding it in an
application helper. The complete CPU framework contract covers repeated generation
transition and a separate interrupted-experiment `Tuner.restore` path.

## Current objective

Reach a repository state worth adopting before broadening the support envelope. A green
mechanics test is necessary but insufficient. The ordinary path, documentation, examples,
packaging, lifecycle recovery, test priorities, failure behavior, and repository hygiene all
need their own evidence.

## Readiness criteria

Before a production-ready claim, the repository should have:

1. a short, framework-native ordinary API with no duplicate configuration or development
   seams exposed to users;
2. self-contained public class/function documentation and a runnable end-to-end example;
3. an explicit scientific-validity boundary beside genome configuration;
4. unit tests for core policy and validation, integration tests for framework seams, and
   end-to-end tests for the user-visible lifecycle rather than tests that freeze file shape;
5. demonstrated checkpoint continuation and interrupted-experiment restoration;
6. a clean install/build path and CI that exercises the distribution artifact rather than
   only an editable checkout;
7. documented resource, failure, compatibility, and support boundaries;
8. useful diagnostics/observability for normal operation and failure;
9. standard repository adoption signals such as a license, security policy, contributing
   guidance, version/release policy, and appropriately scoped dependency metadata; and
10. no archived scaffolding, placeholder modules, negative tests for long-deleted APIs, or
    other development residue in the active tree without a current maintenance purpose.

Current readiness is recorded in root [`STATUS.md`](../STATUS.md).

## Work sequence

### 1. Complete productization review

Keep the public API, README, API guide, example, source exports, and tests aligned with the
framework-native path. Remove obsolete construction scaffolding and keep only durable
architecture/qualification records.

Finish direct qualification of the new no-wrapper runtime discovery and interrupted-run
restore. Review public docstrings and error messages from an external user's perspective.

### 2. Packaging and release hygiene

After the project owner selects a license, add the legal/release metadata needed for
external adoption. Add a security/reporting policy appropriate to the intended support
level and establish the minimal version/changelog/release convention.

CI should eventually build a wheel/sdist and verify a clean non-editable install, but CI
workflow changes remain separately approved work.

Decide whether a static type-checking/PEP 561 support claim is worth maintaining; do not add
a checker merely as a badge if the project will not keep its annotations trustworthy.

### 3. Harden complete-cohort admission and failure behavior

The initial runtime requires enough resources for the complete Clan to become resident and
has a bounded pre-DDP rendezvous timeout.

Investigate the smallest Ray-native mechanism for predictable cohort admission if the
current scheduler/resource interaction can deadlock or fail unclearly. Qualify insufficient
capacity and member failure without creating a second scheduler or taking process-group
ownership from Lightning/PyTorch.

Separately qualify a participant disappearing inside an active framework collective. Do not
claim bounded recovery until healthy participants terminate or recover predictably in the
real path.

### 4. Qualify GPU execution

Run the same public path on CUDA/NCCL. Production code must continue to use the backend and
device visibility supplied by Ray/Lightning/PyTorch rather than introducing a CBT backend
or device selector.

Evidence must cover shared gradients, partitioned training, replicated validation,
member-local divergence, fitness exchange, winner-only checkpoint persistence, full
continuation restore, interrupted-experiment restore where practical, and repeated
generation transition.

Add a realistic GPU optimizer example only after this path is actually qualified.

### 5. Qualify multi-node execution

Extend the one-member/one-rank path across nodes. Resolve only topology and rendezvous gaps
shown by framework evidence. Do not replace the single-node integration with a separate
training system.

### 6. Advanced integration and observability

Qualify user-supplied distributed validation samplers, custom/sharded checkpoint plugins,
and any other extension surface real users require.

Improve Clan-specific diagnostics for cohort formation, round transition, selected source,
mutation, checkpoint provenance, and failure without duplicating Ray/Lightning logging.

### 7. Scientific and operational evidence

Use the public package on realistic optimizer studies. Measure useful round frequencies,
overhead, checkpoint cost, optimizer-policy behavior, and scaling empirically. Examples
should expose costs and limitations, not be engineered to guarantee favorable results.

## Later ClanFSDP work

Model-sharded Clan execution remains a separate later design/qualification effort. It may
require a composed topology representing model shards and Clan members while retaining
framework ownership of the relevant process groups.

## Completion boundary

The current CPU path is a qualified mechanics and lifecycle foundation, not a production
release. Production readiness requires closure of the repository-readiness gaps as well as
broader hardware/failure evidence. All work must preserve the central ownership contract:
CBT supplies/mutates the Tune config; user code owns what its values mean and what they do.
