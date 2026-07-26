# Clan controller API

The Milestone 2 surface consists of three framework-independent objects:
`MutationSpec`, `ClanRound`, and `ClanController`.

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

`standard_deviation`
: Gaussian displacement scale.

`geometry`
: `"linear"` adds the displacement. `"log"` multiplies by its exponential.

`minimum`, `maximum`
: Inclusive bounds applied after mutation.

`mutation.mutate(value, random_stream)` performs the mutation. Mutation specifications
are intentionally trusted internal objects; invalid settings generally fail when the
rule is used rather than through a separate validation subsystem.

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

`member_id`
: Integer identity of the process or trial within the Clan.

`round_index`
: Generation represented by this record.

`config`
: Named controlled values used during this round. The round owns a copy.

`fitness`
: Comparable result. It is `None` until evaluation finishes.

### `get_config()`

Returns a copy of the current round configuration.

### `set_fitness(fitness)`

Stores a finite fitness and immediately calls:

```python
save_member_fitness(round_)
```

The callback decides how the completed round is stored or communicated.

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

`member_id`
: Identity of this local member.

`population_size`
: Fixed number of members expected at every transition.

`initial_config`
: Controlled values supplied for this trial's first round.

`mutations`
: Ordinary dictionary from controlled-value name to `MutationSpec`.

`mode`
: `"min"` or `"max"`. Fitness ties select the lower member ID.

`seed`
: Experiment seed. The controller combines it with `member_id` for a deterministic
member-specific random stream.

`save_member_fitness`
: Callback used by each local `ClanRound` to publish itself.

`load_population`
: Callback receiving a round index and returning `list[ClanRound]` for that completed
round.

`select_winner`
: Callback receiving the winning integer member ID. It applies externally owned
consequences such as model or optimizer transfer; it does not select the winner.

### `get_config()`

Returns this process's controlled values for the current round.

### `set_fitness(fitness)`

Completes and publishes this process's current round.

### `advance()`

Loads the current population, checks that it contains exactly one completed record for
every expected member, selects the winner, calculates this member's next configuration,
calls `select_winner(winner_id)`, and installs the next local `ClanRound`.

The winning member keeps the winning configuration. Every other member mutates from
that same winning configuration.

### `state_dict()` and `load_state_dict(state)`

Save and restore the local random stream together with the current round index,
configuration, and optional fitness. Callback implementations and fixed constructor
settings remain external configuration.

## Framework handoff

A framework integration supplies callback implementations and maps its own trial or
process identity to the controller's integer member ID. It owns synchronization,
checkpoint movement, model and optimizer transfer, pause and resume, and all other
framework lifecycle operations.
