# Clan controller API

The framework-independent surface consists of `MutationSpec`, `ClanRound`, and
`ClanController`.

## `MutationSpec`

```python
from clan_based_tuning import MutationSpec

lr_mutation = MutationSpec(
    standard_deviation=0.25,
    geometry="log",
    minimum=1e-5,
    maximum=1e-2,
)
```

`mutation.mutate(value, random_stream)` applies one bounded linear or logarithmic
mutation. Invalid rules generally fail when used rather than through a separate
validation subsystem.

## `ClanRound`

```python
from clan_based_tuning import ClanRound

round_ = ClanRound(
    member_id=2,
    round_index=4,
    config={"lr": 3e-4},
    save_member_fitness=save_member_fitness,
)
```

`get_config()` returns a copy of the controlled values.

`set_fitness(fitness)` stores a finite fitness and immediately calls
`save_member_fitness(round_)`.

## `ClanController`

```python
from clan_based_tuning import ClanController

controller = ClanController(
    member_id=rank,
    population_size=4,
    initial_config=trial_config,
    mutations={"lr": lr_mutation},
    mode="min",
    seed=17,
    save_member_fitness=save_member_fitness,
    load_population=load_population,
    select_winner=select_winner,
)
```

The constructor settings retain their previous meanings. `select_winner` receives the
selected member ID after the complete current population has been compared.

### `get_config()`

Returns this process's controlled values for the current round.

### `set_fitness(fitness)`

Completes and publishes this process's current round.

### `close_round()`

Loads and validates the complete population for the current round, selects the winner,
records a copy of that completed winning round, calls `select_winner(winner_id)`, and
returns whether the local member is the winner.

The method does not increment the round, mutate a configuration, or install any
next-round state. Its result is intended to gate winner-only checkpoint persistence.

### `state_dict()` and `load_state_dict(state)`

`state_dict()` serializes the current round, deterministic random state, and any
selected completed winner. A winner checkpoint taken after `close_round()` therefore
contains the information needed to manufacture the next population after restoration.

`load_state_dict()` restores the winner-derived state while preserving the receiving
controller's constructor-supplied `member_id`. Missing state keys fail directly.

### `start_next_round()`

Requires a closed winner state that has passed through `load_state_dict()`. It rebases
the restored random stream for the receiving member, keeps the exact winning
configuration for the winning member, mutates from that configuration for every other
member, increments the round, and clears the completed fitness and winner record.

Calling it before restoration raises instead of allowing the old process to continue
past the checkpoint boundary.

## Framework handoff

A framework integration supplies publication and population-loading effects, places the
preferred controller state in the normal winner checkpoint, restores that checkpoint
into every receiver, and calls `start_next_round()` before training resumes.

The controller still does not own synchronization, model or optimizer transfer,
checkpoint I/O, pause and resume, or Tune trial lifecycle.
