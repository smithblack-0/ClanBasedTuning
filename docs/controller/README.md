# Clan controller

Status: Milestone 2 controller contract and implementation

## Lifecycle boundary

One `ClanController` persists beside one training process or trial. It owns that
member's current `ClanRound`, winner selection, local hyperparameter mutation, and
random stream.

The controller does not implement distributed storage, synchronization, model or
optimizer transfer, checkpoints, or framework lifecycle. Those effects are supplied
as callbacks.

## Objects

### `MutationSpec`

A `MutationSpec` applies one bounded mutation rule. Mutation names come from the keys
in the controller's ordinary `dict[str, MutationSpec]`.

### `ClanRound`

A `ClanRound` carries one member's controlled configuration into a training round.
After evaluation, `set_fitness()` attaches the result and passes the completed round
to `save_member_fitness`.

The same object therefore carries configuration into training and fitness back out.
It is not a population wrapper or a framework member.

### `ClanController`

A controller owns only its local member's progression. It never constructs an entire
population. At `advance()` it briefly loads the completed rounds as an ordinary
`list[ClanRound]`, selects the winner, informs the external runtime, and constructs
only its own next round.

## Per-process sequence

Each process follows the same loop:

```python
controller = ClanController(
    member_id=rank,
    population_size=4,
    initial_config=trial_config,
    mutations=mutations,
    mode="min",
    seed=17,
    save_member_fitness=save_member_fitness,
    load_population=load_population,
    select_winner=select_winner,
)

for _ in range(number_of_rounds):
    train(controller.get_config())
    controller.set_fitness(evaluate())
    controller.advance()
```

`set_fitness()` publishes this process's completed round. `advance()` then performs:

```text
load completed rounds
→ verify the expected population
→ select the best round
→ calculate this member's next configuration
→ tell the runtime which member won
→ install this member's next ClanRound
```

All processes load the same completed round and therefore select the same winner.
Each controller calculates only its own next configuration.

## Injected effects

```python
save_member_fitness: Callable[[ClanRound], None]
load_population: Callable[[int], list[ClanRound]]
select_winner: Callable[[int], None]
```

`save_member_fitness` publishes one completed local round.

`load_population` owns rendezvous, storage, and transport. It returns the completed
records for the requested round.

`select_winner` does not choose the winner. The controller calls it with the winning
integer member ID so the surrounding runtime can transfer model, optimizer,
checkpoint, or other externally owned state.

A test can implement these callbacks with an in-memory dictionary. A later Ray
integration can implement the same effects through Tune without changing the core
controller.

## Failure boundary

The controller intentionally performs little validation. Invalid mappings, missing
mutation names, and unusable mutation rules fail naturally when used.

`advance()` retains one explicit corruption guard. The loaded population must contain
exactly one completed result for every expected member and all records must belong to
the requested round. A bad population crashes before winner transfer or installation
of a new round.

`ClanRound.set_fitness()` also rejects non-finite fitness because NaN can otherwise
produce a valid-looking but meaningless winner rather than crashing.

## Randomness and persistence

Each member receives a deterministic local random stream derived from the experiment
seed and integer member ID. `state_dict()` and `load_state_dict()` preserve that stream
together with the current round index, configuration, and optional fitness.

See [API reference](api.md) for the concrete call surface.
