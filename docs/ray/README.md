# Ray integration primitives

Status: first Milestone 3 primitive under review

This directory documents the small components that will eventually connect the accepted
framework-independent controller to Ray Tune. Each component is accepted independently
before the next framework boundary is attached.

## `CompletedRoundStore`

`CompletedRoundStore` is plain in-memory state. It deliberately imports no Ray types and
performs no remote calls. Its single responsibility is to collect one completed plain-data
record from every fixed Clan member and make the same population available to every member.

```python
from clan_based_tuning.ray.round_store import CompletedRoundStore

store = CompletedRoundStore(population_size=2)
store.publish(
    0,
    {
        "member_id": 0,
        "round_index": 0,
        "config": {"lr": 0.1},
        "fitness": 2.0,
    },
)

assert store.read_population(member_id=0, round_index=0) is None

store.publish(
    1,
    {
        "member_id": 1,
        "round_index": 0,
        "config": {"lr": 0.2},
        "fitness": 1.0,
    },
)

population = store.read_population(member_id=0, round_index=0)
assert [record["member_id"] for record in population] == [0, 1]
```

The caller supplies an already resolved integer member identity. The store does not know
about Tune trial IDs, actors, retries, polling, timeouts, winner selection, checkpoints,
or optimizer state.

A population remains unavailable until every member publishes. Once complete, every
member receives a fresh member-ordered copy. After every member has read the population,
the payload is released and the round is permanently closed so late duplicate records
cannot silently create a second scientific event.

## Next integration unit

The next unit may place this store behind one Ray actor and provide the process-local
adapter that implements the controller callbacks:

```python
save_member_fitness: Callable[[ClanRound], None]
load_population: Callable[[int], list[ClanRound]]
```

That later unit must not add checkpointing, Lightning lifecycle hooks, DDP setup, winner
selection, or optimizer application.
