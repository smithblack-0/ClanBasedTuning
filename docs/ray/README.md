# Ray integration

Status: Milestone 3 incremental integration contract

## Explicit Clan member identity

`ClanBasedTraining` currently requires every Tune trial config to contain one stable
integer under `CLAN_MEMBER_ID_KEY` (`"clan_member_id"`). The caller manually creates
exactly one trial for every integer from zero through `population_size - 1`.

```python
from ray import tune

from clan_based_tuning import CLAN_MEMBER_ID_KEY, ClanBasedTraining

population_size = 2
scheduler = ClanBasedTraining(
    population_size=population_size,
    metric="fitness",
    mode="min",
)
param_space = {
    CLAN_MEMBER_ID_KEY: tune.grid_search(list(range(population_size))),
}
```

The scheduler validates uniqueness and range when trials join. When native PBT clones
a source configuration into a target trial, the target retains its own member ID rather
than inheriting the source member's identity.

This ID is the stable logical identity used by the Clan policy. It is not currently a
package-managed DDP rank or process-group assignment. Milestone 3 may manually compose
those external details while the Ray controller-invocation and checkpoint seams are
implemented and reviewed separately.

## Current boundary

This unit does not yet choose how `ClanController` is invoked from the synchronous Tune
population, execute its checkpoint/configuration decision, or define the Lightning
checkpoint hook. Existing Ray/Lightning setup classes remain proof-of-concept evidence
until those later review units settle their contracts.
