import pytest

from clan_based_tuning import ClanController, ClanRound, MutationSpec


class RoundStore:
    def __init__(self, population_size):
        self.population_size = population_size
        self.saved = {}
        self.load_calls = []

    def save(self, round_):
        self.saved[(round_.round_index, round_.member_id)] = round_

    def load(self, round_index):
        self.load_calls.append(round_index)
        return [
            self.saved[(round_index, member_id)]
            for member_id in range(self.population_size)
            if (round_index, member_id) in self.saved
        ]


def _mutation(standard_deviation=0.0):
    return MutationSpec(
        standard_deviation=standard_deviation,
        geometry="linear",
        minimum=0.0,
        maximum=10.0,
    )


def _controller(
    member_id,
    store,
    *,
    initial_value,
    mode="min",
    seed=7,
    standard_deviation=0.0,
):
    return ClanController(
        member_id=member_id,
        population_size=store.population_size,
        initial_config={"lr": initial_value},
        mutations={"lr": _mutation(standard_deviation)},
        mode=mode,
        seed=seed,
        save_member_fitness=store.save,
        load_population=store.load,
    )


def _publish_round(controllers, fitness_values):
    for controller, fitness in zip(controllers, fitness_values, strict=True):
        controller.set_fitness(fitness)


def _load_winner_and_advance(controllers, winner_index):
    winner_state = controllers[winner_index].state_dict()
    for controller in controllers:
        controller.load_state_dict(winner_state)
        controller.advance()
    return winner_state


def test_fake_processes_save_one_winner_then_start_from_its_checkpoint():
    """Only the winner contributes state; every process loads it before mutation."""
    store = RoundStore(population_size=3)
    controllers = [
        _controller(rank, store, initial_value=float(rank + 1)) for rank in range(3)
    ]

    _publish_round(controllers, [4.0, 1.0, 2.0])
    winner_flags = [controller.is_round_winner() for controller in controllers]

    assert winner_flags == [False, True, False]
    assert store.load_calls == [0, 0, 0]

    for controller in controllers:
        with pytest.raises(RuntimeError, match="checkpoint"):
            controller.advance()

    winner_state = _load_winner_and_advance(controllers, winner_index=1)

    assert winner_state == {
        "round_index": 0,
        "config": {"lr": 2.0},
        "fitness": 1.0,
        "winner_id": 1,
    }
    assert [controller.get_config() for controller in controllers] == [
        {"lr": 2.0},
        {"lr": 2.0},
        {"lr": 2.0},
    ]

    _publish_round(controllers, [3.0, 2.0, 4.0])
    assert set(store.saved) >= {(1, 0), (1, 1), (1, 2)}


def test_winner_query_is_cached_for_checkpoint_code():
    """Repeated save-hook checks do not reload the distributed population."""
    store = RoundStore(population_size=2)
    controllers = [
        _controller(rank, store, initial_value=float(rank + 1)) for rank in range(2)
    ]
    _publish_round(controllers, [0.0, 1.0])

    assert controllers[0].is_round_winner()
    assert controllers[0].is_round_winner()
    assert store.load_calls == [0]


def test_max_mode_breaks_ties_by_lower_member_id():
    """Every process reaches the same stable winner when best fitness ties."""
    store = RoundStore(population_size=3)
    controllers = [
        _controller(
            rank,
            store,
            initial_value=float(rank + 1),
            mode="max",
        )
        for rank in range(3)
    ]

    _publish_round(controllers, [5.0, 5.0, 2.0])

    assert [controller.is_round_winner() for controller in controllers] == [
        True,
        False,
        False,
    ]


def test_incomplete_population_crashes_before_checkpoint_selection():
    """A missing member cannot be declared the state source for the next round."""
    store = RoundStore(population_size=3)
    controller = _controller(0, store, initial_value=1.0)
    peer = _controller(1, store, initial_value=2.0)
    controller.set_fitness(1.0)
    peer.set_fitness(2.0)
    state = controller.state_dict()

    with pytest.raises(RuntimeError, match="incomplete"):
        controller.is_round_winner()

    assert controller.state_dict() == state


@pytest.mark.parametrize(
    "rounds, message",
    [
        (
            [
                ClanRound(0, 0, {"lr": 1.0}, lambda round_: None, 1.0),
                ClanRound(0, 0, {"lr": 2.0}, lambda round_: None, 2.0),
                ClanRound(2, 0, {"lr": 3.0}, lambda round_: None, 3.0),
            ],
            "duplicate",
        ),
        (
            [
                ClanRound(0, 0, {"lr": 1.0}, lambda round_: None, 1.0),
                ClanRound(1, 1, {"lr": 2.0}, lambda round_: None, 2.0),
                ClanRound(2, 0, {"lr": 3.0}, lambda round_: None, 3.0),
            ],
            "wrong round",
        ),
    ],
)
def test_population_integrity_guard_rejects_corrupt_rounds(rounds, message):
    controller = ClanController(
        member_id=0,
        population_size=3,
        initial_config={"lr": 1.0},
        mutations={"lr": _mutation()},
        mode="min",
        seed=7,
        save_member_fitness=lambda round_: None,
        load_population=lambda round_index: rounds,
    )

    with pytest.raises(RuntimeError, match=message):
        controller.is_round_winner()


def test_shared_checkpoint_preserves_process_local_deterministic_mutation():
    """Loading one winner does not copy another process's mutable random stream."""
    first_store = RoundStore(population_size=3)
    first = [
        _controller(
            rank,
            first_store,
            initial_value=float(rank + 4),
            seed=17,
            standard_deviation=0.5,
        )
        for rank in range(3)
    ]
    _publish_round(first, [0.0, 1.0, 2.0])
    assert [controller.is_round_winner() for controller in first] == [True, False, False]
    winner_state = _load_winner_and_advance(first, winner_index=0)
    first_configs = [controller.get_config() for controller in first]

    second_store = RoundStore(population_size=3)
    second = [
        _controller(
            rank,
            second_store,
            initial_value=9.0,
            seed=17,
            standard_deviation=0.5,
        )
        for rank in range(3)
    ]
    for controller in second:
        controller.load_state_dict(winner_state)
        controller.advance()
    second_configs = [controller.get_config() for controller in second]

    assert "random_state" not in winner_state
    assert first_configs == second_configs
    assert first_configs[0] == {"lr": 4.0}
    assert first_configs[1] != first_configs[0]
    assert first_configs[2] != first_configs[0]
    assert first_configs[1] != first_configs[2]


def test_advance_requires_a_resolved_winner_even_after_unrelated_restore():
    store = RoundStore(population_size=2)
    controller = _controller(0, store, initial_value=1.0)
    controller.load_state_dict(
        {
            "round_index": 3,
            "config": {"lr": 2.0},
            "fitness": None,
            "winner_id": None,
        }
    )

    with pytest.raises(RuntimeError, match="winner"):
        controller.advance()
