# Milestone 3 gates — integratable orchestration subsystems

Status: active milestone gate  
Date: 2026-07-31

## Milestone result

ClanBasedTuning can be composed through an ordinary Ray Tune function into a real
Lightning DDP workflow that completes multiple generations end to end.

The supported design uses:

- one Tune trial per stable live Clan member;
- one Lightning DDP world spanning those trials;
- one Ray collective population-resolution boundary per generation;
- one thin worker controller with a copied current-genome snapshot and cached local
  checkpoint-source decision;
- one CBT Tune scheduler authoritative over genomes, mutation, lineage, recovery, and
  checkpoint assignment;
- one selected Lightning checkpoint carrying common training continuation and verified
  producer metadata; and
- one target-local child genome carried through each target `Trial.config`.

CBT defines no package-owned `Trainable` subclass, no second training loop, no public
`ClanRound`, and no checkpointed evolutionary controller.

## Capability and responsibility gates

### M3.1 The ordinary Tune function remains the user lifecycle

The public mechanics path has this shape:

```text
read controlled genome from config
→ make worker controller with a copied mapping snapshot
→ obtain any Tune-assigned checkpoint
→ restore training continuation
→ apply current target genome
→ train and evaluate through Lightning
→ provide one local fitness to the controller
→ participate in Ray population resolution
→ selected member retains and annotates the checkpoint
→ report metrics with an optional checkpoint
```

The user does not manually coordinate collective groups, member/rank mapping, complete-
population fitness, comparison policy, mutation state, checkpoint redistribution, or
scheduler lineage.

### M3.2 Ray population resolution preserves the complete Clan

At each qualifying boundary:

- every configured member participates exactly once;
- each valid fitness is associated with one stable member;
- operations from different generations cannot mix;
- the shared deterministic selection policy yields one selected stable member;
- every participant reaches the same result;
- exactly one member is allowed to retain and report the checkpoint; and
- missing, failed, duplicated, malformed, or cross-generation participation fails the
  complete boundary.

The implementation uses Ray collectives. The exact Ray primitive, result shape, identity
encoding, runtime collaborator, and final names are design choices rather than milestone
requirements.

### M3.3 The worker controller remains thin

The worker controller:

- owns one copied current-genome mapping for provenance;
- accepts one finite local fitness;
- enters one Ray population-resolution boundary through the runtime integration;
- caches whether the local stable member is the checkpoint source;
- returns the cached answer on repeated queries without another collective; and
- permits only the selected member to attach producer metadata.

It owns no mutation rule, child genome, scheduler recovery state, replay lineage,
generation advancement, Ray group construction, or serializable continuation.

The current `exchange_fitness` callback and sequence-position identity assumption are
provisional implementation details, not accepted API.

### M3.4 Selection policy is shared and deterministic

Framework-independent evolution policy defines:

- minimizing or maximizing;
- finite fitness requirements;
- stable tie behavior; and
- the selected stable member ID.

The worker-side Ray path and Tune scheduler verification use the same implementation.

### M3.5 The Tune scheduler is the evolutionary authority

For each complete generation, the scheduler:

1. associates every reported fitness with the reporting trial's stable member and active
   genome;
2. selects and verifies one winning trial;
3. verifies that exactly that member supplied the checkpoint;
4. verifies checkpoint producer metadata against that winner;
5. records parent and lineage state;
6. derives one child genome per stable target member;
7. persists mutation RNG, replay, and recovery state;
8. installs each child genome through that target `Trial.config`;
9. assigns the same selected training checkpoint to every target; and
10. releases the complete next population together.

### M3.6 Producer metadata is written before publication

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

The controller writes no generation index, Tune trial ID, fitness, child genomes,
mutation state, or lineage.

The genome is an independently copied mapping snapshot. The contract does not claim
deep immutability for arbitrary nested values.

A failed metadata write prevents checkpoint publication.

### M3.7 Lightning and PyTorch retain native training ownership

Lightning owns Trainer execution, optimizer lifecycle, checkpoint construction,
distributed barriers, and process-group integration. PyTorch DDP supplies native
gradient reduction.

The integration preserves:

- native initial synchronization;
- gradient synchronization across the complete population;
- member-local optimizer history and controlled values;
- intended parameter divergence after local optimizer steps;
- restoration of optimizer history before applying the child genome; and
- winner-aware checkpoint persistence without inventing a second checkpoint format.

The Ray population collective remains a distinct Clan-level coordination boundary.

### M3.8 Fitness is comparable and local

Every member reaches the same logical training boundary and evaluates an equivalent
held-out workload. Fitness remains member-local and is not reduced into one Lightning
metric before CBT population resolution.

### M3.9 Failure and completion are population-wide

A missing or failed member cannot be silently removed while the remaining members
continue as the same Clan.

Collective failure, invalid fitness or identity, inconsistent selected-member results,
missing or multiple checkpoints, producer-metadata disagreement, failed annotation, or
partial target assignment invalidates the generation and releases waiting work through
a surfaced failure.

### M3.10 The scheduler transition has a durable commit boundary

No next-round member may run until:

- the complete generation has reported;
- scheduler and worker-side winner decisions agree;
- producer metadata has been verified;
- all child genomes have been derived;
- scheduler mutation, lineage, and recovery state has been persisted;
- every target configuration contains its assigned child genome; and
- every target has the same selected checkpoint.

A crash before that transition is durably committed restores the last completed
scheduler generation or fails the experiment. It may not release a partial population.

## Test and evidence gates

### M3.11 Focused framework-independent tests protect pure behavior

Unit tests cover:

- minimizing, maximizing, and stable tie behavior;
- finite fitness policy;
- local controller fitness assignment;
- cached one-shot save-decision behavior;
- independent genome mapping ownership;
- winner-only producer metadata writing;
- rejection of unresolved or losing metadata writes;
- absence of worker mutation and serialization APIs; and
- mutation geometry and bounds outside the controller subsystem.

Single-process callback tests do not qualify Ray collective behavior.

### M3.12 Ray framework contracts qualify population resolution

Tests against the pinned Ray version prove:

- complete group construction for the configured population;
- stable member identity association;
- one logical operation per generation boundary;
- identical selected-member results on every participant;
- agreement with the shared pure selection policy;
- no second collective on repeated local save queries;
- surfaced failure for malformed, missing, or failed participation;
- no cross-generation mixing;
- checkpoint metadata update without modifying the Lightning payload;
- Tune result/config access and winner verification;
- target configuration and checkpoint assignment; and
- scheduler persistence and recovery without partial population release.

### M3.13 Lightning framework contracts qualify checkpointing and DDP

Tests against the pinned Lightning and PyTorch versions prove:

- one externally launched Tune worker maps to one Lightning DDP rank;
- the complete population participates in shared-gradient training;
- member-local updates remain divergent;
- optimizer history restores before the child genome is applied;
- every rank enters the required checkpoint boundary; and
- only the selected member retains and annotates a persistent checkpoint.

### M3.14 End-to-end evidence proves repeated real generations

A real multi-member workflow completes at least two transitions and demonstrates:

- one common continuation at generation start;
- target-local child genomes applied after restoration;
- controller snapshots matching the applied genomes;
- shared reduced gradients;
- controlled optimizer-driven divergence;
- comparable local fitness;
- one Ray-resolved checkpoint source;
- one selected checkpoint with correct producer metadata;
- scheduler-assigned child genomes;
- durable scheduler transition state; and
- repeated continuation through Tune and Lightning.

Any accelerator or topology claim requires direct evidence on that accelerator or
topology.

## Documentation and review gates

### M3.15 Documentation separates invariants from implementation choices

Documentation explains:

- the exact high-level Tune function ordering;
- worker, Ray runtime, scheduler, Lightning, and checkpoint responsibilities;
- the fixed Ray-collective population invariants;
- the still-open Ray primitive, data-shape, identity, and interface choices;
- scheduler authority versus checkpoint provenance;
- atomicity and failure boundaries; and
- tested support limitations.

### M3.16 Pull request descriptions remain synchronized with diffs

Every PR states:

- the exact files and behavior changed;
- which design decisions are introduced versus merely inherited;
- which tests are unit fakes versus direct framework evidence; and
- the explicit exclusions of the slice.

A PR must not describe planned behavior as implemented or silently re-endorse provisional
code from an earlier iteration.

### M3.17 A public mechanics example exposes the ordinary path

A reproducible example uses the supported function API, completes multiple real
generations, and makes gradients, divergence, fitness, population resolution, producer
metadata, child genomes, inherited optimizer state, scheduler recovery, and continued
training inspectable.

### M3.18 Milestone 4 receives the proven ordinary sequence

The handoff identifies the remaining user-facing assembly steps a later usability
frontend may remove, the lower-level primitives it must preserve, and the tested support
boundary it may not broaden silently.

## Closure evidence

Milestone 3 closes with the accepted architecture, focused pure tests, direct Ray and
Lightning framework contracts, repeated end-to-end evidence, engineering and support
documentation, a public mechanics example, human review, and a Milestone 4 handoff.
