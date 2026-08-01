# Worker controller

Status: current implementation and redesign boundary  
Date: 2026-07-31

## Purpose

`ClanController` is the worker-facing object used at one completed training boundary.
Its long-term role is narrow:

- own one worker's local boundary state;
- participate in the accepted Ray collective population-resolution path through the
  runtime integration;
- cache whether the local stable member is the checkpoint source; and
- later, let only that selected member attach producer-genome metadata.

The controller is not the evolutionary policy owner. The CBT Tune scheduler owns
mutation, child genomes, lineage, recovery, target configuration, and checkpoint
redistribution.

## Current implementation

The active framework-independent constructor is:

```python
controller = ClanController(
    member_id=member_id,
    population_size=population_size,
    mode="min",
    exchange_fitness=exchange_fitness,
)
```

The current object:

1. stores one finite local fitness through `set_fitness()`;
2. calls `exchange_fitness(local_fitness)` on the first
   `should_save_checkpoint()` query;
3. expects one fitness value per population member in sequence order;
4. selects a winner through `select_winner_id()`;
5. caches whether `member_id` is the selected sequence position; and
6. returns the cached Boolean on later queries.

This code is framework-independent and its tests use Python fakes. It is not a Ray
collective implementation.

## Why the current interface is provisional

The current callback:

```python
exchange_fitness(local_fitness) -> Sequence[float]
```

does not adequately document or own the distributed contract.

In particular, it leaves implicit:

- that the production mechanism is a Ray collective;
- how collective groups are created and torn down;
- why sequence position corresponds to stable member identity;
- how one generation's operation is isolated from another;
- what happens when a member fails or never participates;
- which layer owns timeout and failure release;
- whether the controller should receive all member fitness or only the selected member;
  and
- which component applies the shared selection policy.

The callback name, callable shape, constructor fields, sequence data shape, validation
placement, and current docstrings are therefore not accepted API merely because the
implementation is merged.

## Accepted intrinsic requirements

The redesign must preserve these requirements:

- one live Tune trial represents one stable Clan member;
- every required member contributes one comparable fitness at the same logical boundary;
- population resolution uses a Ray collective;
- fitness is associated with stable member identity;
- all successful participants reach the same deterministic selected member;
- exactly one local controller caches `True` for checkpoint retention;
- repeated queries and later provenance checks do not repeat the collective;
- missing, failed, duplicated, malformed, or cross-generation participation fails the
  complete boundary; and
- the Tune scheduler independently selects and verifies the same member.

See [Ray population-resolution design](../design/population_resolution.md).

## Responsibility boundaries under review

The redesign must separate these roles clearly:

- **Ray runtime:** group membership, transport, generation isolation, timeout, and
  failure behavior;
- **evolution policy:** deterministic minimizing/maximizing selection and tie behavior;
- **worker controller:** local fitness, one participation boundary, cached local answer,
  and later producer metadata;
- **Tune scheduler:** authoritative generation transition and verification.

The exact object boundary and final names are still under review. The next implementation
must be derived from that review rather than from a rename of `exchange_fitness` or an
opaque `fitness -> bool` callback.

## Accepted worker ordering

The high-level flow remains:

```text
train and evaluate one member
→ controller receives one local fitness
→ controller participates in one Ray population-resolution operation
→ local checkpoint-source answer is cached
→ every Lightning rank enters the checkpoint boundary
→ selected member retains the checkpoint
→ selected member writes producer metadata
→ report metrics, with a checkpoint only from that member
```

## Planned producer provenance

After the Ray interface is accepted, the controller will also receive an independently
copied mapping of the current scheduler-assigned genome.

Only the selected member will be allowed to write:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

before reporting the checkpoint.

The contract is ownership of a separate top-level mapping snapshot. Deep immutability of
arbitrary nested values is not currently required or proven.

The provenance guard reads the already cached save decision and performs no second Ray
collective.

## Explicit non-responsibilities

The controller does not own:

- child-genome derivation;
- mutation random state;
- scheduler lineage or recovery;
- Tune checkpoint assignment;
- Lightning checkpoint construction;
- model or optimizer state;
- generation advancement; or
- serializable continuation of itself.

## Current development rule

No controller provenance or Ray-runtime implementation should be accepted until the
population-resolution interface has been reviewed at the level of:

- Ray primitive;
- result data shape;
- stable identity representation;
- component boundary and names;
- failure and timeout behavior;
- generation isolation; and
- direct multiprocess evidence.
