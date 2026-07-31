# Clan controller

Status: Milestone 2 controller with the accepted Milestone 3 lifecycle correction

## Lifecycle boundary

One `ClanController` persists beside one training process or trial. It owns that
member's current `ClanRound`, winner selection, winner-derived controller state,
member-local mutation, and deterministic random stream.

The controller does not implement distributed storage, synchronization, model or
optimizer transfer, checkpoints, or framework lifecycle. Those effects remain external.

## Why the lifecycle is split

A completed winner must be checkpointed before any next-round mutation is manufactured.
The controller therefore has two separate transitions:

```text
complete and publish the current round
→ close_round(): select and record the completed winner
→ checkpoint and restore the winning controller state
→ start_next_round(): rebase and manufacture this member's next round
```

`close_round()` never increments the round or mutates a configuration.
`start_next_round()` refuses to run until a closed winner state has been restored.

## Objects

### `MutationSpec`

A `MutationSpec` applies one bounded mutation rule. Mutation names come from the keys
in the controller's ordinary `dict[str, MutationSpec]`.

### `ClanRound`

A `ClanRound` carries one member's controlled configuration into a training round.
After evaluation, `set_fitness()` attaches the result and passes the completed round
to `save_member_fitness`.

### `ClanController`

A controller owns only its local member's progression. It briefly loads the completed
population when closing a round, records the selected completed round, and exposes that
state for checkpointing. After the winning state is restored into each receiver, the
controller rebases its random stream for the receiving member and creates only that
member's next round.

## Small manual lifecycle

```python
from clan_based_tuning import ClanController, MutationSpec


class RoundStore:
    def __init__(self, population_size):
        self.population_size = population_size
        self.saved = {}

    def save(self, round_):
        self.saved[(round_.round_index, round_.member_id)] = round_

    def load(self, round_index):
        return [
            self.saved[(round_index, member_id)]
            for member_id in range(self.population_size)
            if (round_index, member_id) in self.saved
        ]


population_size = 3
store = RoundStore(population_size)
winner_calls = [[] for _ in range(population_size)]
mutations = {
    "lr": MutationSpec(
        standard_deviation=0.0,
        geometry="linear",
        minimum=0.0,
        maximum=10.0,
    )
}
controllers = [
    ClanController(
        member_id=member_id,
        population_size=population_size,
        initial_config={"lr": float(member_id + 1)},
        mutations=mutations,
        mode="min",
        seed=17,
        save_member_fitness=store.save,
        load_population=store.load,
        select_winner=winner_calls[member_id].append,
    )
    for member_id in range(population_size)
]

for controller, fitness in zip(controllers, [4.0, 1.0, 2.0], strict=True):
    controller.set_fitness(fitness)

preferred = [controller.close_round() for controller in controllers]
assert preferred == [False, True, False]
assert winner_calls == [[1], [1], [1]]

winning_state = controllers[1].state_dict()
for controller in controllers:
    controller.load_state_dict(winning_state)
    controller.start_next_round()

assert [controller.get_config() for controller in controllers] == [
    {"lr": 2.0},
    {"lr": 2.0},
    {"lr": 2.0},
]
```

The explicit `state_dict()` transfer stands in for the future winner-only Lightning
checkpoint. It demonstrates the required order without implementing a checkpoint or
training framework in the controller package.

## Injected effects

```python
save_member_fitness: Callable[[ClanRound], None]
load_population: Callable[[int], list[ClanRound]]
select_winner: Callable[[int], None]
```

`save_member_fitness` publishes one completed local round.

`load_population` returns the complete records for the requested round. The controller
keeps its corruption guard at this policy boundary.

`select_winner` receives the selected integer member ID after local selection. It may
record lineage or set framework-owned winner context, but it does not transfer state or
manufacture the next round.

## Failure boundary

`close_round()` rejects incomplete, duplicated, wrong-round, or fitness-less
populations before recording a winner or invoking `select_winner`.

`start_next_round()` rejects open rounds and locally selected state that has not passed
through `load_state_dict()`. This prevents the pre-checkpoint process from mutating and
continuing from its local trajectory.

`ClanRound.set_fitness()` rejects non-finite fitness before publication.

## Randomness and persistence

`state_dict()` includes the current round, random state, and selected completed winner.
Only the preferred process's state should enter the continuation checkpoint.

`load_state_dict()` restores that common winner-derived state while retaining the
receiving controller's member ID. `start_next_round()` derives a deterministic child
stream for that member from the restored winner stream. Consequently, the same winning
checkpoint produces the same member-local next population regardless of the constructor
seed used to recreate a receiving process, while no losing random trajectory survives.

See [API reference](api.md) for the concrete call surface.
