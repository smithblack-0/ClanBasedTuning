# Milestone 3 gates — integratable orchestration subsystems

Status: active milestone gate  
Date: 2026-07-31  
Population-resolution clarification: 2026-08-01

## Milestone result

ClanBasedTuning can be composed through an ordinary Ray Tune function into a real
Lightning DDP workflow that completes multiple generations end to end.

The supported design uses:

- one Tune trial per live Clan member;
- one Lightning DDP world spanning the complete live population;
- a thin worker `ClanController` holding worker-local boundary state and producer
  provenance;
- a CBT Tune scheduler owning population genomes, mutation, lineage, recovery, and
  checkpoint assignment;
- one selected Lightning checkpoint carrying the common training continuation and
  producer metadata; and
- target-local child genomes carried through each target `Trial.config`.

CBT defines no package-owned `Trainable` subclass, no second training loop, no public
`ClanRound`, and no checkpointed evolutionary controller.

The mechanism that resolves one checkpoint source from the complete pre-report fitness
population remains open. Milestone 3 must select and qualify it from current framework
evidence rather than inherit the provisional PR #33 callback.

## Capability and responsibility gates

### M3.1 The ordinary Tune function remains the user lifecycle

The public mechanics path has this shape:

```text
read controlled genome from config
→ make worker controller with a copied genome snapshot
→ obtain any Tune-assigned checkpoint
→ restore training continuation
→ apply current target genome
→ train and evaluate through Lightning
→ provide local fitness to the controller
→ obtain one local checkpoint-source decision
→ selected worker constructs and annotates the checkpoint
→ report metrics with an optional checkpoint
```

The user does not manually coordinate population synchronization, comparison policy,
mutation state, checkpoint redistribution, or scheduler lineage.

### M3.2 The worker controller remains thin

The worker controller:

- copies the current controlled genome mapping at construction;
- accepts one finite local fitness;
- obtains one local checkpoint-source answer through the runtime integration;
- caches that answer so repeated queries do not repeat population synchronization; and
- permits only the resolved selected worker to annotate a checkpoint.

It owns no communication backend, group lifecycle, mutation rule, child genome,
scheduler recovery state, replay lineage, generation advancement, or serializable
continuation.

The current `exchange_fitness` callback and its docstrings are provisional. The accepted
controller API must be rewritten from the current requirements rather than copied from
that implementation.

### M3.3 The pre-report population-resolution seam is selected from current evidence

The accepted implementation must prove:

- every required member participates at the same logical fitness boundary;
- exactly one comparable fitness value is associated with each stable member;
- the same comparison direction and stable tie rule determine one winner;
- exactly one worker receives the checkpoint-source answer;
- a missing, failed, duplicate, invalid, or cross-generation result prevents advance;
- repeated local queries return a cached answer; and
- failure releases or terminates the full population rather than hanging indefinitely.

The milestone must explicitly decide and document:

- whether the existing PyTorch process group or a Ray mechanism owns the communication;
- whether full fitness values or only a final decision are communicated;
- rank and member identity mapping;
- initialization, teardown, timeout, and failure behavior;
- generation separation; and
- the narrow public and internal interfaces.

No gate requires a Ray collective, PyTorch all-gather, callback named
`exchange_fitness`, or a module named `ray_collective.py`.

### M3.4 The Tune scheduler is the evolutionary authority

For each complete generation, the scheduler:

1. associates every reported fitness with the reporting trial's active genome;
2. selects and verifies one winning trial;
3. verifies that exactly that trial supplied the checkpoint;
4. verifies producer metadata against that winner;
5. records the winning parent genome and lineage;
6. derives one child genome per stable target member;
7. persists mutation RNG, replay, checkpoint reference, and recovery state;
8. installs each child genome through that target `Trial.config`;
9. assigns the same selected training checkpoint to every target; and
10. releases the complete next population together.

### M3.5 Producer metadata is written before publication

After Lightning constructs the selected checkpoint, the selected controller writes:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

The controller does not write generation identity, Tune trial identity, fitness, child
genomes, mutation state, or lineage.

The selected worker must complete this metadata write before `tune.report()` publishes
the checkpoint. A failed write prevents publication of an incomplete artifact.

### M3.6 Genome authority and provenance remain distinct

The CBT Tune scheduler is authoritative over population genomes and mutation lineage.
The current trial configuration is its assigned live genome for that worker.

The controller owns an independent copied mapping used only for producer provenance. No
deep-immutability contract for arbitrary nested values is implied.

The scheduler rejects any checkpoint whose metadata disagrees with the selected winner's
member ID or controlled trial configuration.

### M3.7 Lightning and PyTorch retain native training ownership

Lightning owns Trainer execution, optimizer lifecycle, checkpoint construction,
distributed barriers, and process-group integration. PyTorch DDP supplies native
gradient reduction.

The CBT integration preserves:

- native initial synchronization;
- gradient synchronization across the complete population;
- member-local optimizer history and controlled values;
- intended parameter divergence after local optimizer steps; and
- winner-aware checkpoint persistence without inventing a second checkpoint format.

### M3.8 Fitness is comparable and local

Every member reaches the same logical training boundary and evaluates an equivalent
held-out workload. Fitness remains member-local and is not reduced into one Lightning
metric before CBT compares the population.

### M3.9 A broken active population fails as a whole

A missing or failed member cannot be silently removed while the remaining members
continue as the same Clan. Invalid population resolution, missing or multiple
checkpoints, producer disagreement, failed metadata attachment, or partial target
assignment invalidates the generation.

### M3.10 The scheduler transition has a durable commit boundary

No next-round member may run until:

- the complete generation has reported;
- the winner and sole checkpoint source agree;
- producer metadata has been verified;
- all child genomes have been derived;
- scheduler mutation and lineage state required for recovery has been persisted;
- every target configuration contains its assigned child genome; and
- every target has the same selected checkpoint.

A crash before that transition is durably committed must restore the last completed
scheduler generation or fail the experiment.

## Test and evidence gates

### M3.11 Focused tests protect framework-independent contracts

Unit tests cover:

- minimizing, maximizing, and stable lower-member tie behavior;
- finite local fitness;
- one-shot cached checkpoint-source resolution;
- controller ownership of a copied genome mapping;
- winner-only producer annotation;
- the minimal metadata schema;
- rejection of unresolved or losing annotation attempts;
- absence of worker mutation and serialization APIs; and
- mutation geometry and bounds outside the controller subsystem.

Unit tests may inject a transport-neutral resolver. They must not claim that a fake
Python callback proves a distributed collective.

### M3.12 Framework contracts qualify the chosen population-resolution seam

After the seam is selected, direct tests against the pinned framework versions prove:

- membership and stable identity mapping;
- communication initialization and teardown;
- one complete and correctly ordered population result;
- no cross-generation mixing;
- timeout or failure release;
- one consistent checkpoint-source answer; and
- compatibility with the Lightning DDP process lifecycle.

Evidence must name the exact chosen backend. Tests for an unselected mechanism are
research evidence, not active implementation contracts.

### M3.13 Ray framework contracts qualify Tune lifecycle seams

Tests against the pinned Ray version prove:

- scheduler access to results and active trial configurations;
- checkpoint metadata readback and winner/config verification;
- target configuration replacement;
- selected-checkpoint assignment to every target;
- function-trial restoration through `tune.get_checkpoint()`;
- optional checkpoint reporting through `tune.report()`; and
- scheduler persistence and recovery without partial population release.

### M3.14 Lightning framework contracts qualify checkpointing and DDP

Tests against the pinned Lightning and PyTorch versions prove:

- one externally launched Tune worker maps to one Lightning DDP rank;
- the complete population participates in shared-gradient training;
- member-local updates remain divergent;
- optimizer history restores before the child genome is applied;
- every rank enters the required checkpoint boundary; and
- only the selected member retains and annotates a persistent checkpoint.

### M3.15 End-to-end evidence proves repeated real generations

A real multi-member workflow completes at least two transitions and demonstrates:

- one common continuation at generation start;
- target-local child genomes applied after restoration;
- controller snapshots matching the applied genomes;
- shared reduced gradients;
- controlled optimizer-driven divergence;
- comparable local fitness;
- one selected and annotated checkpoint;
- scheduler-assigned child genomes;
- durable scheduler transition state; and
- repeated continuation through Tune and Lightning.

Any accelerator or topology claim requires direct evidence on that accelerator or
topology.

## Documentation and example gates

### M3.16 Engineering documentation transfers the complete model

Documentation explains:

- the exact imperative Tune function;
- worker, scheduler, Tune configuration, Lightning, and checkpoint responsibilities;
- the chosen population-resolution mechanism and why it was selected;
- the distinction between scheduler authority and checkpoint provenance;
- producer annotation ordering;
- scheduler transition atomicity;
- failure boundaries; and
- tested support limitations.

### M3.17 A public mechanics example exposes the ordinary path

A reproducible example uses the supported API, completes multiple real generations, and
makes gradients, divergence, fitness, producer genome, checkpoint provenance, child
genomes, inherited optimizer state, scheduler recovery state, and continued training
inspectable.

### M3.18 An initial scientific workload begins evaluating the method

A public-package experiment uses a real task capable of illustrating optimizer-genome
adaptation, records its workload, generation policy, fitness, compute cost, and
limitations, and reports favorable, neutral, or unfavorable results honestly.

## Review and handoff gates

### M3.19 The complete workflow is internally consistent

Implementation, tests, framework evidence, documentation, examples, PR descriptions,
and module names describe one supported workflow and the exact scope actually delivered.

No artifact may claim that a callback fake is a production collective, that a test-only
PR implements a contract, or that a design-only PR changed runtime behavior.

### M3.20 Milestone 4 receives the proven ordinary sequence

The handoff identifies the remaining user-facing assembly steps a later usability
frontend may remove, the lower-level primitives it must preserve, and the tested support
boundary it may not silently broaden.

## Closure evidence

Milestone 3 closes with the accepted architecture, focused core tests, direct framework
contracts for the chosen seams, repeated end-to-end evidence, engineering and support
documentation, a public mechanics example, initial scientific results, human review, and
a Milestone 4 handoff.
