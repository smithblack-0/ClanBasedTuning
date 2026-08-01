# Milestone 3 contract: integratable orchestration

Status: active milestone gate

## Result

ClanBasedTuning can be manually composed through an ordinary Ray Tune function into a real Lightning DDP workflow that completes multiple Clan generations end to end.

The milestone is integratable rather than yet convenient: package-managed DDP, model wrapping, and distributed-data setup remain Milestone 4 work.

## Required capability

### Worker path

The supported worker path:

- reads its controlled genome from `Trial.config`;
- constructs the worker controller through the integration layer;
- restores any assigned Lightning checkpoint;
- reapplies the current target genome without clearing inherited optimizer history;
- trains and evaluates through Lightning;
- resolves the checkpoint source through the complete Ray population boundary;
- enters the distributed Lightning checkpoint boundary on every required rank;
- lets only the selected member retain and annotate the checkpoint; and
- reports metrics, with a checkpoint only from that member.

The controller remains thin and has no mutation, generation-advance, recovery, or serializable evolutionary state.

### Scheduler path

The CBT Tune scheduler:

- waits for one result from every required member;
- associates fitness with stable member identity and active genome;
- independently selects and verifies the winner;
- verifies the sole checkpoint and its producer metadata;
- derives one child genome per target;
- persists mutation RNG, lineage, recovery, and transition state;
- installs target configurations and the common selected checkpoint; and
- releases the complete next population together.

### Framework ownership

- PyTorch DDP owns ordinary gradient synchronization.
- Lightning owns training, validation, optimizer lifecycle, checkpoint construction, and restoration.
- Ray owns trial execution and the population collective transport.
- ClanBasedTuning owns only the Clan-specific selection, provenance, mutation, verification, and transition behavior.

## Required evidence

### Focused core evidence

Tests cover:

- minimizing, maximizing, and deterministic tie behavior;
- one selected source from a complete population;
- rejection of invalid local or population fitness;
- one-shot cached population resolution;
- independent genome copying;
- winner-only producer annotation;
- minimal producer metadata;
- rejection of unresolved or losing annotation;
- mutation geometry and bounds outside the worker controller; and
- absence of worker evolution and serialization APIs.

### Ray qualification

Against the pinned Ray version, direct tests establish:

- collective group creation and complete member-associated fitness exchange;
- stable member-to-participant association;
- optional winner-only checkpoint reporting and restoration through the ordinary function path;
- scheduler access to results and active trial configurations;
- target configuration and checkpoint assignment;
- scheduler persistence and recovery; and
- surfaced failure without partial-population continuation.

### Lightning and PyTorch qualification

Against the pinned Lightning and PyTorch versions, direct tests establish:

- the complete live Clan participates in shared-gradient training;
- member-local optimizer behavior produces intended divergence;
- optimizer history restores before the target genome is applied;
- every required rank enters the checkpoint boundary; and
- only the selected member retains a persistent checkpoint.

### End-to-end evidence

A real multi-member workflow completes at least two generation transitions and demonstrates the active system behavioral contracts together.

Any backend, accelerator, device-count, or topology claim requires direct evidence on that path.

## Documentation and examples

Milestone 3 documentation must explain the ordinary Tune function, state authority, population-resolution contract, checkpoint provenance, scheduler transition, failure boundaries, and actual support envelope without requiring reconstruction from historical records.

A public mechanics example must use the supported package path and make common restoration, shared gradients, member divergence, local fitness, selected provenance, child genomes, and continued training inspectable.

An initial public-package scientific workload must record its setup, generation policy, fitness, compute cost, limitations, and results without requiring a favorable outcome.

## Closure

Milestone 3 closes only when implementation, focused tests, direct framework qualification, repeated end-to-end evidence, documentation, examples, scientific evidence, and human review describe one coherent supported workflow.

The Milestone 4 handoff identifies only the external assembly steps that usability work may remove; it does not replace or broaden the lower-level contracts proven here.
