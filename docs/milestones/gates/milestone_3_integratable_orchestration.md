# Milestone 3 gates — integratable orchestration subsystems

Status: active milestone gate  
Date: 2026-07-31

## Milestone result

ClanBasedTuning can be composed through an ordinary Ray Tune function into a real
Lightning DDP workflow that completes multiple generations end to end.

The supported design uses:

- one Tune trial per live Clan member;
- one Lightning DDP world spanning those trials;
- a thin worker `ClanController` that holds one immutable current-genome snapshot,
  performs the pre-report fitness collective, decides the local checkpoint source, and
  lets only that source write producer metadata;
- a CBT Tune scheduler that owns population genomes, mutation, lineage, recovery, and
  checkpoint assignment;
- one selected Lightning checkpoint carrying the common training continuation and the
  winning producer's member ID and genome; and
- target-local child genomes carried through each target `Trial.config`.

CBT defines no package-owned `Trainable` subclass, no second training loop, no public
`ClanRound`, and no checkpointed evolutionary controller.

## Capability and responsibility gates

### M3.1 The ordinary Tune function remains the user lifecycle

The public mechanics path has this shape:

```text
read controlled genome from config
→ make worker controller with a copy of that genome
→ obtain any Tune-assigned checkpoint
→ restore training continuation
→ apply current target genome
→ train and evaluate through Lightning
→ set fitness on worker controller
→ ask whether this worker should save
→ selected worker constructs the checkpoint
→ selected worker saves its genome into checkpoint metadata
→ report metrics with an optional checkpoint
```

The user does not manually coordinate rank, collective groups, complete-population
fitness, comparison policy, mutation state, checkpoint redistribution, or scheduler
lineage.

### M3.2 The worker controller remains thin

The worker controller:

- copies the current controlled genome mapping at construction;
- accepts one finite local fitness;
- performs one complete-population fitness exchange;
- applies the shared stable winner-selection rule;
- returns whether the local worker is the checkpoint source;
- caches the decision so repeated calls cannot re-enter the collective; and
- permits only the selected worker to call `save_genome(checkpoint)`.

It owns no mutation rule, child genome, scheduler recovery state, replay lineage, round
advancement, or serializable continuation.

### M3.3 The Tune scheduler is the evolutionary authority

For each complete generation, the scheduler:

1. associates every reported fitness with the reporting trial's active genome;
2. selects and verifies one winning trial;
3. verifies that exactly that trial supplied the checkpoint;
4. verifies the checkpoint producer metadata against that winner;
5. records the winning parent genome and lineage;
6. derives one child genome per stable target member;
7. persists mutation RNG, replay, and recovery state;
8. installs each child genome through that target `Trial.config`;
9. assigns the same selected training checkpoint to every target; and
10. releases the complete next population together.

The scheduler decides genomes. `Trial.config` is the live materialization of those
assignments for each active worker.

### M3.4 Producer metadata is written before publication

After Lightning constructs the selected checkpoint, the winning controller writes:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

The controller does not write a round index or Tune trial ID because it does not own
those scheduler facts. It does not write fitness, child genomes, mutation state, or
lineage.

The selected worker must finish this metadata write before `tune.report()` publishes
the checkpoint. A failed write prevents publication of an incomplete artifact.

### M3.5 Genome authority and provenance remain distinct

The CBT Tune scheduler is authoritative over population genomes and mutation lineage.
The current trial configuration is its assigned live genome for that worker.

The controller's genome is an immutable copy used only for winner provenance. The
checkpoint metadata records which member and genome produced the payload. It does not
own receiving child genomes or future mutation decisions.

The scheduler must reject any checkpoint whose metadata disagrees with the selected
winner's member ID or controlled trial configuration.

### M3.6 Lightning and PyTorch retain native training ownership

Lightning owns Trainer execution, optimizer lifecycle, checkpoint construction,
distributed barriers, and process-group integration. PyTorch DDP supplies native
gradient reduction.

The CBT integration preserves:

- native initial synchronization;
- gradient synchronization across the complete population;
- member-local optimizer history and controlled values;
- intended parameter divergence after local optimizer steps; and
- winner-aware checkpoint persistence without inventing a second checkpoint format.

### M3.7 Fitness is comparable and local

Every member reaches the same logical training boundary and evaluates an equivalent
held-out workload. Fitness remains member-local and is not reduced into one Lightning
metric before CBT compares the population.

### M3.8 A broken active population fails collectively

A missing or failed member cannot be silently removed while the remaining members
continue as the same Clan. Collective failure, invalid result populations, missing or
multiple checkpoints, producer-metadata disagreement, failed metadata attachment, or
partial target assignment invalidate the generation.

### M3.9 The scheduler transition has a durable commit boundary

No next-round member may run until:

- the complete generation has reported;
- the winner and sole checkpoint source agree;
- producer metadata has been verified;
- all child genomes have been derived;
- scheduler mutation and lineage state required for recovery has been persisted;
- every target configuration contains its assigned child genome; and
- every target has the same selected checkpoint.

A crash before that transition is durably committed must restore the last completed
scheduler generation or fail the experiment. It may not release a partially assigned
population.

## Test and evidence gates

### M3.10 Focused tests protect core contracts

Unit tests cover:

- one checkpoint source from a complete population;
- minimizing, maximizing, and stable lower-rank tie behavior;
- finite local and collective fitness requirements;
- cached one-shot collective resolution;
- controller copying rather than retaining the caller's genome mapping;
- winner-only `save_genome(checkpoint)`;
- the minimal `{schema_version, member_id, genome}` metadata schema;
- rejection of unresolved or losing metadata writes;
- the absence of worker mutation and serialization APIs;
- shared winner-selection behavior intended for worker and scheduler reuse; and
- mutation geometry and bounds outside the controller subsystem.

### M3.11 Ray framework contracts qualify the runtime seams

Tests against the pinned Ray version prove:

- actor-local collective initialization and ordered fitness all-gather;
- scheduler access to results and reporting trials' current configurations;
- selected-worker checkpoint metadata update without loading or modifying the Lightning
  payload;
- checkpoint metadata readback and winner/config verification;
- target configuration replacement;
- selected-checkpoint assignment to every target;
- function-trial restoration through `tune.get_checkpoint()`;
- optional checkpoint reporting through `tune.report()`; and
- scheduler persistence and recovery without partial population release.

### M3.12 Lightning framework contracts qualify checkpointing and DDP

Tests against the pinned Lightning and PyTorch versions prove:

- one externally launched Tune worker maps to one Lightning DDP rank;
- the complete population participates in shared-gradient training;
- member-local updates remain divergent;
- optimizer history restores before the child genome is applied;
- every rank enters the required checkpoint boundary; and
- only the selected member retains and annotates a persistent checkpoint.

### M3.13 End-to-end evidence proves repeated real generations

A real multi-member workflow completes at least two transitions and demonstrates:

- one common continuation at generation start;
- target-local child genomes applied after restoration;
- controller snapshots matching the applied genomes;
- shared reduced gradients;
- controlled optimizer-driven divergence;
- comparable local fitness;
- one selected checkpoint;
- correct winner-side producer metadata;
- scheduler-assigned child genomes;
- durable scheduler transition state; and
- repeated continuation through Tune and Lightning.

Any accelerator or topology claim requires direct evidence on that accelerator or
topology.

## Documentation and example gates

### M3.14 Engineering documentation transfers the complete model

Documentation explains:

- the exact imperative Tune function;
- worker, scheduler, Tune configuration, Lightning, and checkpoint responsibilities;
- the distinction between scheduler authority and checkpoint provenance;
- the minimal producer metadata schema;
- winner-side annotation ordering;
- scheduler transition atomicity;
- mutation and checkpoint-assignment ordering;
- failure boundaries; and
- tested support limitations.

### M3.15 A public mechanics example exposes the ordinary path

A reproducible example uses the supported function API, completes multiple real
generations, and makes gradients, divergence, fitness, producer genome, checkpoint
provenance, child genomes, inherited optimizer state, scheduler recovery state, and
continued training inspectable.

### M3.16 An initial scientific workload begins evaluating the method

A public-package experiment uses a real task capable of illustrating optimizer-genome
adaptation, records its workload, generation policy, fitness, compute cost, and
limitations, and reports favorable, neutral, or unfavorable results honestly.

## Review and handoff gates

### M3.17 The complete workflow is internally consistent

Implementation, tests, framework evidence, documentation, examples, and module names
describe one supported workflow and one owner for every decision or state transition.

In particular, mutation and scheduler transition behavior must not remain under a
`controller_types` namespace after the thin-controller boundary is adopted.

### M3.18 Milestone 4 receives the proven ordinary sequence

The handoff identifies the remaining user-facing assembly steps a later usability
frontend may remove, the lower-level primitives it must preserve, and the tested
support boundary it may not silently broaden.

## Closure evidence

Milestone 3 closes with the accepted architecture, focused core tests, direct Ray and
Lightning framework contracts, repeated end-to-end evidence, engineering and support
documentation, a public mechanics example, initial scientific results, human review,
and a Milestone 4 handoff.
