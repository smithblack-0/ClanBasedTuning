# Population-resolution responsibilities

Status: Milestone 3 design candidate  
Date: 2026-07-31

## Purpose

This document assigns ownership for satisfying the
[population-resolution invariants](population_resolution_invariants.md).

It fixes authority boundaries where ambiguity could duplicate policy or hide lifecycle
state. It deliberately does not freeze internal transport representation, backend,
device placement, constructor shape, or helper names.

## Semantic boundary

The Ray population runtime accepts one member's local fitness at one generation boundary
and returns a complete association between stable Clan members and their fitness values.

That sentence is the contract. The concrete Python type is not architectural.

A successful result must contain exactly one finite comparable fitness for every required
stable member. The mapping between a Ray collective participant and a stable member must
be explicit or mechanically proven; incidental sequence position is insufficient unless
its meaning is established by the runtime contract.

## Ray population runtime

The Ray-specific population runtime owns:

- collective-group construction, membership, and teardown;
- the mapping between stable member identity and collective participation;
- population communication at one qualifying generation boundary;
- returning complete member-associated fitness information;
- preventing contributions from different generations from mixing;
- surfacing timeout, participant failure, malformed transport output, and incomplete
  participation; and
- releasing waiting participants when the boundary fails.

It does not own:

- minimizing or maximizing policy;
- tie-breaking policy;
- winner selection;
- mutation or child-genome derivation;
- scheduler lineage or recovery;
- checkpoint construction; or
- Tune result reporting.

The architecture commits to Ray collective communication for this role. The exact Ray
primitive, backend, device, dtype, internal result container, and implementation object
name are implementation decisions.

## Framework-independent selection policy

The shared selection function owns:

- comparison direction;
- comparison-validity rules;
- stable deterministic tie behavior; and
- selection of one stable member from complete member-associated fitness.

The worker-side path and Tune scheduler use the same implementation. The Ray population
runtime does not contain a second winner-selection rule.

`select_winner_id()` currently represents this policy in `evolution.py`. A later rename
is allowed only if ownership and the single-policy invariant remain unchanged.

## Worker controller

`ClanController` owns the worker-facing state and ordering:

- the stable identity of its local member;
- comparison mode;
- one local fitness value;
- one invocation of the Ray population runtime;
- application of the shared selection policy to the complete result;
- one cached local save decision; and
- later, the copied current genome and winner-only producer-provenance write.

The controller does not create or destroy Ray collective groups. It does not expose
collective membership or transport buffers to the user training function. It does not
mutate genomes, derive child configurations, advance generations, or persist scheduler
state.

The accepted user-facing behavior remains:

```python
controller.set_fitness(fitness)
should_save = controller.should_save_checkpoint()
```

and later, only after a cached winning decision:

```python
checkpoint = controller.save_genome(checkpoint)
```

The constructor, internal collaborator interface, and concrete population-result type are
not public architectural commitments.

## Worker integration factory

The worker integration constructs and wires the controller and Ray population runtime.
It obtains runtime identity, population membership, comparison configuration, generation
context, and collective configuration without requiring the user training function to
assemble those details manually.

The intended public entry point remains conceptually:

```python
controller = make_cbt_controller(genome=genome)
```

The exact factory signature may evolve while implementation evidence is gathered. Its
responsibility does not: hide framework wiring while preserving the ordinary Tune
function shape.

## Tune scheduler

The CBT Tune scheduler owns the authoritative generation transition. It:

- waits for one result from every required trial;
- associates each reported fitness with the correct stable member and active genome;
- applies the same shared selection policy independently;
- verifies that exactly the selected member supplied the checkpoint;
- verifies checkpoint producer metadata;
- derives child genomes;
- persists mutation, lineage, and recovery state;
- installs target configurations and the common selected checkpoint; and
- releases the next population only after the transition is complete.

The scheduler does not trust the worker-side result as authority. Worker resolution makes
one pre-report checkpoint possible; scheduler verification decides whether the generation
transition is accepted.

## Lightning and PyTorch

Lightning owns training-loop and checkpoint boundaries. PyTorch DDP owns shared-gradient
communication.

Every required training process participates in the Lightning checkpoint boundary. Only
the selected member retains the persistent continuation passed to Tune.

The Ray population runtime does not replace DDP gradient communication, and DDP does not
replace the Ray population-resolution boundary.

## Failure ownership

Each layer fails the facts it owns:

- the worker controller rejects invalid local lifecycle use;
- the selection policy rejects invalid comparison input;
- the Ray population runtime surfaces communication, membership, timeout, and generation
  isolation failures;
- Lightning surfaces checkpoint-construction failure; and
- the Tune scheduler rejects incomplete or inconsistent generation transitions.

No layer may convert a failure into a valid partial-population winner.
