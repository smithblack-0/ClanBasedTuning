# Milestone 3 gates — integratable orchestration subsystems

Status: active milestone gate  
Date: 2026-07-31

## Milestone result

ClanBasedTuning can be composed through an ordinary Ray Tune function into a real
Lightning DDP workflow that completes multiple generations end to end.

The supported design uses:

- one Tune trial per live Clan member;
- one Lightning DDP world spanning those trials;
- a thin worker `ClanController` that performs only the pre-report fitness collective
  and local checkpoint-source decision;
- a CBT Tune scheduler that owns genomes, mutation, lineage, and checkpoint assignment;
- one selected Lightning checkpoint carrying the common training continuation; and
- target-local child genomes carried through each target `Trial.config`.

CBT defines no package-owned `Trainable` subclass, no second training loop, no public
`ClanRound`, and no checkpointed worker controller.

## Capability and responsibility gates

### M3.1 The ordinary Tune function remains the user lifecycle

The public mechanics path has this shape:

```text
make worker controller
→ obtain any Tune-assigned checkpoint
→ restore training continuation
→ apply current target genome from config
→ train and evaluate through Lightning
→ set fitness on worker controller
→ ask whether this worker should save
→ report metrics with an optional checkpoint
```

The user does not manually coordinate rank, collective groups, complete-population
fitness, comparison policy, mutation state, checkpoint redistribution, or scheduler
lineage.

### M3.2 The worker controller is only a collective save-decision handle

The worker controller:

- accepts one finite local fitness;
- performs one complete-population fitness exchange;
- applies the shared stable winner-selection rule;
- returns whether the local worker is the checkpoint source; and
- caches the decision so repeated calls cannot re-enter the collective.

It owns no genome, mutation, Tune configuration, model state, checkpoint, scheduler
state, round advancement, or serializable continuation.

### M3.3 The Tune scheduler is the sole evolutionary authority

For each complete generation, the scheduler:

1. associates every reported fitness with the reporting trial's active genome;
2. selects and verifies one winning trial;
3. verifies that exactly that trial supplied the checkpoint;
4. records the winning parent genome and lineage;
5. derives one child genome per stable target member;
6. installs each child genome through that target `Trial.config`;
7. assigns the same selected training checkpoint to every target; and
8. releases the next complete population together.

Mutation RNG, replay history, and scheduler recovery state belong to the scheduler.

### M3.4 Genome and checkpoint authority remain separate

The active genome is the controlled subset of one trial's Tune configuration.

The shared checkpoint payload contains model state, optimizer history, Lightning
progress, and other supported training continuation. It does not contain several
receiving members' child genomes.

After selecting the winner, the scheduler attaches checkpoint provenance metadata
containing:

- schema version;
- completed generation identity;
- source member identity;
- source Tune trial identity; and
- the winning parent genome.

The parent metadata binds the artifact to the genome that produced it. Each receiving
child genome remains authoritative in its target trial configuration.

### M3.5 Lightning and PyTorch retain native training ownership

Lightning owns Trainer execution, optimizer lifecycle, checkpoint construction,
distributed barriers, and process-group integration. PyTorch DDP supplies native
gradient reduction.

The CBT integration preserves:

- native initial synchronization;
- gradient synchronization across the complete population;
- member-local optimizer history and controlled values;
- intended parameter divergence after local optimizer steps; and
- winner-aware checkpoint persistence without inventing a second checkpoint format.

### M3.6 Fitness is comparable and local

Every member reaches the same logical training boundary and evaluates an equivalent
held-out workload. Fitness remains member-local and is not reduced into one Lightning
metric before CBT compares the population.

### M3.7 A broken active population fails collectively

A missing or failed member cannot be silently removed while the remaining members
continue as the same Clan. Collective failure, invalid result populations, missing or
multiple checkpoints, genome/provenance disagreement, failed metadata attachment, or
partial target assignment invalidate the generation.

## Test and evidence gates

### M3.8 Focused tests protect core contracts

Unit tests cover:

- one checkpoint source from a complete population;
- minimizing, maximizing, and stable lower-rank tie behavior;
- finite local and collective fitness requirements;
- cached one-shot collective resolution;
- the absence of worker mutation and serialization APIs;
- shared winner-selection behavior intended for worker and scheduler reuse;
- mutation geometry and bounds; and
- parent-genome checkpoint metadata schema and input ownership.

### M3.9 Ray framework contracts qualify the runtime seams

Tests against the pinned Ray version prove:

- actor-local collective initialization and ordered fitness all-gather;
- scheduler access to results and reporting trials' current configurations;
- target configuration replacement;
- selected-checkpoint assignment to every target;
- function-trial restoration through `tune.get_checkpoint()`;
- optional checkpoint reporting through `tune.report()`;
- scheduler persistence and recovery; and
- checkpoint metadata update without loading the Lightning payload.

### M3.10 Lightning framework contracts qualify checkpointing and DDP

Tests against the pinned Lightning and PyTorch versions prove:

- one externally launched Tune worker maps to one Lightning DDP rank;
- the complete population participates in shared-gradient training;
- member-local updates remain divergent;
- optimizer history restores before the child genome is applied;
- every rank enters the required checkpoint boundary; and
- only the selected member retains a persistent checkpoint.

### M3.11 End-to-end evidence proves repeated real generations

A real multi-member workflow completes at least two transitions and demonstrates:

- one common continuation at generation start;
- target-local child genomes applied after restoration;
- shared reduced gradients;
- controlled optimizer-driven divergence;
- comparable local fitness;
- one selected checkpoint;
- correct parent-genome provenance;
- scheduler-assigned child genomes; and
- repeated continuation through Tune and Lightning.

Any accelerator or topology claim requires direct evidence on that accelerator or
topology.

## Documentation and example gates

### M3.12 Engineering documentation transfers the complete model

Documentation explains:

- the exact imperative Tune function;
- worker, scheduler, Tune configuration, Lightning, and checkpoint authority;
- the genome/checkpoint distinction;
- parent-genome metadata;
- mutation and checkpoint-assignment ordering;
- failure boundaries; and
- tested support limitations.

### M3.13 A public mechanics example exposes the ordinary path

A reproducible example uses the supported function API, completes multiple real
generations, and makes gradients, divergence, fitness, parent genome, checkpoint
provenance, child genomes, inherited optimizer state, and continued training
inspectable.

### M3.14 An initial scientific workload begins evaluating the method

A public-package experiment uses a real task capable of illustrating optimizer-genome
adaptation, records its workload, generation policy, fitness, compute cost, and
limitations, and reports favorable, neutral, or unfavorable results honestly.

## Review and handoff gates

### M3.15 The complete workflow is internally consistent

Implementation, tests, framework evidence, documentation, and examples describe one
supported workflow and one state authority for every piece of data.

### M3.16 Milestone 4 receives the proven ordinary sequence

The handoff identifies the remaining user-facing assembly steps a later usability
frontend may remove, the lower-level primitives it must preserve, and the tested
support boundary it may not silently broaden.

## Closure evidence

Milestone 3 closes with the accepted architecture, focused core tests, direct Ray and
Lightning framework contracts, repeated end-to-end evidence, engineering and support
documentation, a public mechanics example, initial scientific results, human review,
and a Milestone 4 handoff.
