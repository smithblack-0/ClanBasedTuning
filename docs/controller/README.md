# Clan controller

Status: accepted controller contract with Milestone 3 checkpoint handoff

## Lifecycle boundary

One `ClanController` persists beside one training process or Tune trial. It owns that
member's current `ClanRound`, complete-population fitness comparison, and local
optimizer-hyperparameter mutation.

The controller does not implement distributed result transport, synchronization,
checkpoint creation, checkpoint transport, framework restoration, model movement, or
optimizer construction. Two callbacks publish completed rounds and retrieve one
complete population. Framework checkpoint code depends on the controller to learn
whether its local process owns the winning state.

## Objects

### `MutationSpec`

A `MutationSpec` applies one bounded mutation rule. Mutation names come from the keys
in the controller's ordinary `dict[str, MutationSpec]`.

### `ClanRound`

A `ClanRound` carries one member's controlled configuration into a training round.
After evaluation, `set_fitness()` attaches the result and passes the completed round
to `save_member_fitness`.

The callback name describes publication, not disk persistence. A Ray integration may
translate the completed round into a Tune result dictionary; an in-memory test may
store the object directly.

### `ClanController`

A controller owns only its local member's policy progression. At a completed round it
can retrieve the complete population and answer `is_round_winner()`. The surrounding
checkpoint lifecycle saves only that winner, loads the same winning checkpoint into
every process, and then calls `advance()` so each process manufactures its own next
`ClanRound` from the restored parent.

## Process-local sequence

```text
LOAD THE WINNING CHECKPOINT
  ├── restore the completed winning model and optimizer state
  ├── restore controller winner state while preserving local member identity
  ├── controller.advance()
  ├── read controller.get_config()
  └── apply the local optimizer configuration
  ▼
TRAIN
  │
  │ qualifying round boundary
  ▼
controller.set_fitness(local_fitness)
  │
  │ completed local round is published
  ▼
controller.is_round_winner()
  ├── retrieve the complete population
  ├── select and cache one winner
  └── return whether this process owns that winner
  ▼
AM I THE WINNER?
  ├── yes → save the one shared winning checkpoint
  └── no  → do not save
  ▼
WAIT UNTIL THE WINNING CHECKPOINT IS READY
  └────────────────────────────────────────► LOAD THE WINNING CHECKPOINT
```

Selection therefore chooses a parent state. Checkpointing preserves that parent.
Mutation occurs only after every process restores the same parent.

## Small process mock

The framework-independent ordering can be exercised without a model, optimizer, Ray,
Lightning, or filesystem:

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
    )
    for member_id in range(population_size)
]

for controller, fitness in zip(controllers, [4.0, 1.0, 2.0], strict=True):
    controller.set_fitness(fitness)

winner_flags = [controller.is_round_winner() for controller in controllers]
assert winner_flags == [False, True, False]

# This stands in for the single checkpoint written by the winning process.
winning_checkpoint = controllers[1].state_dict()

# This stands in for every process loading that same checkpoint.
for controller in controllers:
    controller.load_state_dict(winning_checkpoint)
    controller.advance()

assert [controller.get_config() for controller in controllers] == [
    {"lr": 2.0},
    {"lr": 2.0},
    {"lr": 2.0},
]
```

With nonzero mutation, member 1 still retains the winning configuration while members
0 and 2 derive deterministic local perturbations only after the common checkpoint is
loaded.

This remains a framework-independent contract exercise. The real manual CPU
Ray/Lightning/PyTorch workflow is a Milestone 3 acceptance gate.

## Injected effects

```python
save_member_fitness: Callable[[ClanRound], None]
load_population: Callable[[int], list[ClanRound]]
```

`save_member_fitness` publishes one completed local round. It does not prescribe disk
storage or checkpointing.

`load_population` owns the asynchronous or synchronous rendezvous needed to return the
complete records for one round. The controller validates completeness before choosing
a winner.

Checkpoint integration receives the controller as a dependency:

```python
if controller.is_round_winner():
    save_winning_checkpoint()

wait_for_winning_checkpoint()
load_winning_checkpoint()
controller.advance()
apply_optimizer_config(controller.get_config())
```

The exact save, wait, load, and restore hooks belong to the Milestone 3 framework
integration.

## Failure boundary

The controller intentionally performs little validation. Invalid mappings, missing
mutation names, and unusable mutation rules fail naturally when used.

`is_round_winner()` retains one explicit corruption guard. The loaded population must
contain exactly one completed result for every expected member and all records must
belong to the requested round.

`advance()` refuses to run until a resolved winning checkpoint has been loaded. This
prevents a losing process from mutating its stale local state and prevents the winner
from advancing before the checkpoint captures the selected parent.

`ClanRound.set_fitness()` rejects non-finite fitness because NaN can otherwise produce
a valid-looking but meaningless winner.

## Randomness and persistence

The constructor seed belongs to the local trial configuration. Mutation derives a
fresh standard-library `random.Random` stream from the seed, local member ID, and next
round index. The stream is deterministic but is not stored in the common winning
checkpoint.

`state_dict()` contains the completed round and cached winner ID. `load_state_dict()`
restores that shared parent while preserving local member identity, callbacks,
mutation rules, mode, and seed.

See [API reference](api.md) for the concrete call surface.
