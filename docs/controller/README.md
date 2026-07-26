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
`list[ClanRound]`, selects the winner, manufactures only its own next round, informs
the external runtime, and installs that prepared round.

## Fake multi-process loop

The framework-independent lifecycle can be exercised with ordinary in-memory mocks:

```python
class RoundStore:
    def __init__(self, population_size):
        self.population_size = population_size
        self.saved = {}

    def save(self, round_):
        self.saved[(round_.round_index, round_.member_id)] = round_

    def load(self, round_index):
        return [self.saved[(round_index, member_id)] for member_id in range(self.population_size)]


population_size = 3
store = RoundStore(population_size)
winner_calls = [[] for _ in range(population_size)]
controllers = [
    ClanController(
        member_id=member_id,
        population_size=population_size,
        initial_config=initial_configs[member_id],
        mutations=mutations,
        mode="min",
        seed=17,
        save_member_fitness=store.save,
        load_population=store.load,
        select_winner=winner_calls[member_id].append,
    )
    for member_id in range(population_size)
]

for _ in range(number_of_rounds):
    for controller in controllers:
        train(controller.get_config())
        controller.set_fitness(evaluate(controller))

    for controller in controllers:
        controller.advance()
```

The first inner loop stands in for parallel training and reporting. The second stands
in for every process observing the complete round, selecting the same winner,
transferring externally owned state through `select_winner`, and installing its own
next `ClanRound`.

## Advance sequence

`advance()` performs:

```text
load completed rounds
→ verify the expected population
→ select the best round
→ manufacture this member's complete next ClanRound
→ tell the runtime which member won
→ install the prepared ClanRound
```

Mutation is part of manufacturing the next round from the winning round. All local
calculation therefore finishes before `select_winner` can transfer model, optimizer,
or checkpoint state.

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

A later Ray integration can implement these effects through Tune without changing
the core controller.

## Replay

The selected winner ID is also the event needed to record a PBT replay path. The core
controller should continue to emit that event through `select_winner`; durable lineage
storage, association with checkpoints and round identities, and execution of a later
replay run belong to Milestone 3 because they depend on the external lifecycle.

No additional replay object or callback is required in Milestone 2. The Milestone 3
integration can transfer the selected state through each local callback while one
authority records the winner idempotently for the completed round.

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
