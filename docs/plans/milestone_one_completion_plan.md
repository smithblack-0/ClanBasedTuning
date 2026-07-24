# Milestone-one completion and handoff plan

Status: proposed execution plan  
Date: 2026-07-24  
Governing documents:
[`product_roadmap.md`](../product_roadmap.md),
[`framework_alignment_findings.md`](../research/framework_alignment_findings.md),
[`framework_alignment_gates.md`](../gates/framework_alignment_gates.md)

## Objective

Complete framework-alignment research with enough accepted evidence that the
evolutionary subsystem can be designed and implemented without reopening basic
framework ownership on every issue.

Milestone one is complete only when:

- the research conclusions have been reviewed and corrected by a human;
- the invariant gates have been accepted;
- high-risk upstream seams have executable contract probes;
- unresolved questions are assigned to the milestone that must answer them;
- the next implementation can be audited against a small, coherent contract.

The objective is not to preserve or polish the current proof-of-concept source.

## Workstream 1: human review and decision closure

### Purpose

Separate accepted project decisions from research hypotheses before code work
uses them as constraints.

### Actions

1. Review the framework-alignment findings section by section.
2. Mark each conclusion as accepted, revised, rejected, or deferred.
3. Apply accepted changes to both the findings and gate file in the same change.
4. Keep unresolved implementation questions in the evidence ledger; do not hide
   them in code comments or issue descriptions.
5. Confirm that no current source component is treated as authoritative merely
   because it already exists.

### Exit evidence

- reviewed findings;
- accepted gate file;
- no unresolved disagreement about the algorithm, round ownership, population
  authority, framework ownership, or initial recovery boundary.

## Workstream 2: convert fragile findings into executable contracts

### Purpose

Replace source-reading confidence with direct evidence at every private or
version-sensitive seam that the next milestone will depend on.

### Required probes

1. **Exclusive-parent synchronous PBT**
   - at least three Tune trials;
   - one deterministic winner;
   - every other trial receives the winner checkpoint;
   - one exact elite configuration;
   - independent target mutations;
   - two consecutive generations.

2. **Member-local Lightning checkpointing**
   - every Clan rank writes its own trial-local checkpoint;
   - Ray's standard Lightning callback reports it once at validation end;
   - PBT can use a non-DDP-global-zero member as the source.

3. **Optimizer reconciliation**
   - inherited SGD momentum and AdamW moments match the source;
   - target optimizer configuration is applied after restore;
   - unsupported bindings fail rather than silently no-op.

4. **Native DDP initialization and divergence**
   - initial model and buffer synchronization;
   - no subsequent buffer broadcast;
   - common reduced gradients;
   - divergent parameters after member-local optimizer steps;
   - exact supported Lightning hook documented.

5. **Population admission**
   - Ray `num_samples` used as the sole population input;
   - default variant generator with no grid expansion;
   - generated count confirmed equal to `num_samples`;
   - `max_concurrent_trials` required to equal `num_samples`;
   - insufficient devices or concurrency rejected before DDP setup;
   - complete population enters the rendezvous together;
   - no actor reuse.

### Implementation discipline

Each probe should be the smallest executable test that establishes one upstream
contract. It should not become a hidden product implementation. When a probe
requires private source assumptions, record the exact upstream revision and the
failure message expected when the assumption changes.

### Exit evidence

- committed framework-contract tests;
- test names mapped to evidence-ledger claims;
- dependency ranges narrow enough to make the claims meaningful.

## Workstream 3: resolve only the blockers needed by the evolutionary subsystem

### Purpose

Prevent milestone two from absorbing Lightning orchestration or later recovery
work while still giving the controller a complete public contract.

### Decisions required before milestone two implementation

1. **Winner and tie policy**
   - deterministic score direction and stable tie rule;
   - exact elite policy;
   - behavior for missing, NaN, and infinite fitness.

2. **Mutation boundary**
   - optimizer-only keys or explicit nested optimizer configuration;
   - validation that mutation cannot alter model, data, or other
     gradient-defining configuration;
   - no second optimizer schema in the controller.

3. **Collective planned completion**
   - one owner for deciding that the synchronized population should terminate;
   - no Tune per-trial stop condition;
   - no second round clock;
   - final best result and checkpoint remain inspectable.

4. **Failure contract**
   - one member error stops or fails the complete clan;
   - no independent recovery;
   - useful failure context and finite wait behavior.

### Explicitly deferred from milestone two

- Lightning validation scheduling;
- DDP rendezvous and model wrapping;
- member-local Lightning checkpoint implementation;
- dataloader construction;
- subepoch continuation;
- whole-experiment recovery;
- checkpoint pruning and shared retention;
- polished ordinary-user assembly.

### Exit evidence

A controller design can be stated in one short contract: given a complete set of
member fitness results and Tune trial state at a synchronized boundary, choose
one parent, produce optimizer-only next configurations, transfer through native
PBT behavior, and either continue or stop the complete population.

## Workstream 4: prepare the milestone-three integration questions

### Purpose

Record the integration work that must follow the controller without designing it
prematurely inside milestone two.

### Milestone-three gates to investigate

1. Which Lightning `val_check_interval` configurations provide deterministic,
   synchronized subepoch validation across members?
2. How does Lightning resume the exact training and dataloader position after a
   subepoch checkpoint under each supported loader type?
3. What is the narrowest Strategy seam for trial-local checkpoint writing on
   every Clan rank?
4. How is the receiving trial's current optimizer configuration made available
   at the restore seam without a second configuration authority?
5. Which standard PyTorch sampler configuration best expresses replicated
   deterministic fitness data?
6. Which external-rank environment and rendezvous responsibilities are truly
   Clan-specific, and which can remain ordinary Lightning Strategy setup?
7. Which precision and accumulation configurations preserve the common-gradient
   contract?

These are recorded now so the controller does not accidentally absorb them.
They should not be decomposed into implementation issues until milestone one is
accepted and milestone two is underway or complete, consistent with the roadmap.

## Revision and review procedure

Every document or implementation produced from this plan receives the following
passes before acceptance:

1. **Contract:** one owner and one main idea per component or document section.
2. **DRY and boundary:** remove duplicate counters, configuration, validation,
   checkpoint authority, and lifecycle state.
3. **Design improvement:** eliminate machinery that exists only to compensate
   for an earlier ownership error.
4. **Documentation:** explain lifecycle, authority, surprising framework
   constraints, and support boundaries to a blind reader.
5. **Adversarial:** trace fresh launch, normal round, winner transfer, collective
   stop, member failure, and unsupported restore in source order.

A passing test does not override a failed ownership review. A concise design does
not override missing failure behavior. A framework-native design does not excuse
an unusable integration.

## Handoff to milestone two

Milestone two begins only after the accepted gate file and required PBT probes
are available. Its first deliverable is a documented, independently invokable
evolutionary controller—not a Trainer facade, DDP automation layer, or complete
end-to-end package.

The implementation should be reviewed against four questions:

1. Does it express the sole-parent Clan transition exactly?
2. Does it delegate ordinary PBT lifecycle behavior to Ray rather than
   reimplementing it?
3. Is every mutable value restricted to optimizer-side configuration?
4. Can the controller be understood and tested without constructing the later
   Lightning integration?
