# Clan controller API

The framework-independent surface consists of three objects: `MutationSpec`,
`ClanRound`, and `ClanController`.

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

The callback decides how the completed round is stored or communicated. Its name does
not imply checkpoint or filesystem persistence.

## `ClanController`

```python
from clan_based_tuning import ClanController

controller = ClanController(
    member_id=rank,
    population_size=4,
    initial_config=trial_config,
    mutations={"lr": lr_mutation},
    mode="min",
    seed=trial_seed,
    save_member_fitness=save_member_fitness,
    load_population=load_population,
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
: Stable local trial seed. Mutation combines it with `member_id` and the next round
index. The seed remains constructor configuration and is not inherited through the
common winner checkpoint.

`save_member_fitness`
: Callback used by each local `ClanRound` to publish itself.

`load_population`
: Callback receiving a round index and returning `list[ClanRound]` for that completed
round. It may block or yield through an external asynchronous runtime until the
complete population exists.

### `get_config()`

Returns this process's controlled values for the current round.

### `set_fitness(fitness)`

Completes and publishes this process's current round.

### `is_round_winner()`

Loads and validates the complete current population, selects one stable winner, caches
its integer member ID, and returns whether the local process is that winner. Repeated
calls for the same round use the cached decision rather than reloading the population.

Checkpoint lifecycle code uses the answer before mutation:

```python
if controller.is_round_winner():
    save_winning_checkpoint()
```

### `advance()`

Constructs this member's next `ClanRound` only after the common winning checkpoint has
been loaded. The restored winner member retains the winning optimizer configuration;
every other member mutates from that same restored configuration.

Calling `advance()` before winner resolution or before loading the winning checkpoint
raises `RuntimeError`.

### `state_dict()`

Returns:

```python
{
    "round_index": int,
    "config": dict[str, float],
    "fitness": float | None,
    "winner_id": int | None,
}
```

The winner saves this state after `is_round_winner()` and before `advance()`. The
common checkpoint intentionally excludes mutable RNG state and local member identity.

### `load_state_dict(state)`

Restores the common completed winner state and cached winner ID while preserving the
receiving process's local member identity, trial seed, callbacks, mutation rules, and
mode. A later `advance()` derives that process's next configuration.

## Framework handoff

A framework integration supplies the two callbacks, injects the controller into its
checkpoint lifecycle, and maps framework trial/process identity to integer member ID.
It owns:

- result transport and complete-population rendezvous;
- deciding when the winner saves;
- making the winning checkpoint available;
- restoring that checkpoint in every process;
- applying `controller.get_config()` to the restored optimizer;
- pause, resume, and distributed execution; and
- durable replay history aligned with framework round and checkpoint identity.

The controller owns only the winner decision and local next-configuration policy.
