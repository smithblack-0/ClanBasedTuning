# Milestone 3 gates — integratable orchestration subsystems

Status: working rewrite for review

## Milestone result

The public evolutionary controller and Clan-specific integration primitives can be manually composed into a real distributed Lightning workflow that completes repeated Clan rounds through native Ray Tune, Lightning, and PyTorch behavior.

## Capability and responsibility gates

### M3.1 The manual workflow preserves framework ownership

The workflow explicitly composes Ray trials and PBT execution, Lightning training and validation, PyTorch DDP, model and optimizer construction, data configuration, the public controller, and the minimal Clan-specific seams. It introduces no second training loop, checkpoint system, population scheduler, or collective implementation.

### M3.2 One live population is admitted coherently

The complete Tune population, concurrent resources, Clan rank/world size, rendezvous data, and DDP membership describe one concurrently resident Clan or setup fails before distributed work begins.

### M3.3 Native DDP provides shared gradients without erasing member divergence

Members receive the same reduced gradient from independently partitioned training batches while their local optimizer state and configuration produce divergent parameters. Initial synchronization and runtime buffer behavior preserve the intended inherited state and divergence.

### M3.4 Lightning produces the real Clan boundary

The integration defines the qualifying Lightning validation-and-checkpoint event that ends a round. Sanity checks, unrelated validation, and intermediate logging do not trigger evolution. Every member reaches the same logical boundary and reports one comparable member-local fitness value.

### M3.5 Training and fitness data have the accepted semantics

Training uses normal distributed partitioning. Fitness evaluation uses the same held-out workload under equivalent ordering, transforms, and length for every member, and candidate fitness is not reduced across members before Ray compares it.

### M3.6 The native checkpoint-driven transition forms the next generation

At the qualifying boundary:

- each divergent member supplies the trial-local Lightning checkpoint and report required by Ray;
- Ray PBT applies the controller decision and assigns the winning member's checkpoint and target configuration through its native lifecycle;
- Lightning restores the winning model and optimizer state in each next-generation trial;
- ClanBasedTuning reapplies only the receiving member's evolved optimizer values after optimizer restoration;
- the recreated trials form the next DDP group and continue training from one inherited parent state.

This is the normal Clan round transition. It is not a separate operational recovery subsystem.

### M3.7 Failure of one active member invalidates the active Clan

A missing or failed member cannot be silently removed while the remaining population continues as a valid Clan. The supported workflow terminates or fails clearly enough to identify the affected member and lifecycle boundary.

## Test gates

### M3.8 Focused tests cover every Clan-specific integration primitive

Direct tests cover the primitive's contract, lifecycle position, ownership boundary, state ordering, and failure behavior, including population/rank preflight, boundary selection, fitness reporting, member-local checkpoint permission, and optimizer-value reconciliation.

### M3.9 Framework-contract tests protect the seams the integration relies upon

Tests against each qualified framework version exercise only the assumptions material to the public integration, including DDP synchronization behavior, Lightning boundary/report/checkpoint ordering, Ray assignment of the selected checkpoint and configuration, Lightning optimizer restoration order, and post-restore optimizer reconciliation.

Exact versions belong to reproducible test environments; published dependency constraints express the compatibility range actually qualified by these tests.

### M3.10 End-to-end tests prove repeated real Clan rounds

Using the public manual composition, at least three concurrently resident members complete at least two rounds and demonstrate:

- common reduced gradients from independent training data;
- optimizer-driven member divergence;
- comparable local fitness;
- one selected parent;
- native checkpoint/configuration assignment;
- inherited model and optimizer state;
- evolved target optimizer values applied after restore;
- reformed DDP execution and continued training.

Any accelerator claim requires a direct accelerator run. CPU evidence qualifies only the CPU topology it exercises.

### M3.11 Negative tests protect the declared integration boundary

The workflow rejects or fails clearly on inconsistent population/resources/ranks, unsupported boundary or loader semantics, fitness reduction that erases candidate differences, missing trial-local checkpoints, conflicting optimizer or scheduler authority, and active member loss.

## Documentation gates

### M3.12 Engineering documentation enables manual integration and review

The milestone delivers an integration design and ownership map, a manual composition guide, reference documentation for each Clan-specific primitive and required framework setting, a tested support/limitations statement, and failure-boundary guidance. A reviewer can follow one complete round from training through evaluation, controller decision, native checkpoint transition, DDP reformation, and continued training.

## Example and scientific-work gates

### M3.13 A public mechanics example exposes the complete workflow

A reproducible manual-composition example completes multiple real rounds and makes shared gradients, divergence, fitness, selected parent, target configurations, checkpoint lineage, inherited state, and continued training inspectable. It uses no private shortcut unavailable to an advanced integrator.

### M3.14 An initial scientific workload begins evaluating the method honestly

A public-package experiment uses a real task capable of illustrating optimizer-policy adaptation, records the workload, members, round cadence, policy path, fitness, cost, and limitations, and reports favorable, neutral, or unfavorable results. It establishes that the integrated product can investigate the method; it need not establish that the method is valuable.

## Evidence, review, and handoff gates

### M3.15 The complete manual workflow is internally consistent

Implementation, focused tests, framework-contract tests, end-to-end results, documentation, and examples describe one supported manual workflow. Human review applies the standing framework-native review to every custom seam.

### M3.16 Milestone 4 receives the proven manual sequence

The handoff identifies the exact user-facing assembly steps that may be removed, the lower-level public primitives the convenience path must compose, the tested support boundary it must preserve, and the advanced manual path that remains available.

## Closure evidence

Milestone 3 closes with links to the integration design, primitive and framework-contract tests, multi-round end-to-end results, manual integration and support documentation, mechanics example, scientific workload and results, human review, and Milestone 4 handoff.