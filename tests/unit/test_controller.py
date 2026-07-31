import pytest

from clan_based_tuning import ClanController, ClanRound, MutationSpec


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


class RandomValueMutation:
    def mutate(self, value, random_stream):
        return random_stream.random()


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
    winner_calls,
    *,
    initial_value,
    mode="min",
    seed=7,
    mutations=None,
):
    return ClanController(
        member_id=member_id,
        population_size=store.population_size,
        initial_config={"lr": initial_value},
        mutations=mutations or {"lr": _mutation()},
        mode=mode,
        seed=seed,
        save_member_fitness=store.save,
        load_population=store.load,
        select_winner=winner_calls.append,
    )


def test_close_round_selects_without_manufacturing_the_next_round():
    """Selection closes the evaluated round but leaves its state checkpointable."""
    store = RoundStore(population_size=3)
    winner_calls = [[], [], []]
    controllers = [
        _controller(rank, store, winner_calls[rank], initial_value=float(rank + 1))
        for rank in range(3)
    ]

    for controller, fitness in zip(controllers, [4.0, 1.0, 2.0], strict=True):
        controller.set_fitness(fitness)

    states_before_close = [controller.state_dict() for controller in controllers]
    preferred = [controller.close_round() for controller in controllers]

    assert preferred == [False, True, False]
    assert winner_calls == [[1], [1], [1]]
    for controller, state_before_close in zip(controllers, states_before_close, strict=True):
        state_after_close = controller.state_dict()
        assert state_after_close["round_index"] == state_before_close["round_index"] == 0
        assert state_after_close["config"] == state_before_close["config"]
        assert state_after_close["fitness"] == state_before_close["fitness"]
        assert state_after_close["selected_winner"]["member_id"] == 1


def test_max_mode_breaks_ties_by_lower_member_id_without_advancing():
    store = RoundStore(population_size=3)
    winner_calls = [[], [], []]
    controllers = [
        _controller(
            rank,
            store,
            winner_calls[rank],
            initial_value=float(rank + 1),
            mode="max",
        )
        for rank in range(3)
    ]

    for controller, fitness in zip(controllers, [5.0, 5.0, 2.0], strict=True):
        controller.set_fitness(fitness)
    preferred = [controller.close_round() for controller in controllers]

    assert preferred == [True, False, False]
    assert winner_calls == [[0], [0], [0]]
    assert [controller.state_dict()["round_index"] for controller in controllers] == [0, 0, 0]


def test_start_next_round_requires_a_closed_restored_round():
    store = RoundStore(population_size=2)
    controller = _controller(0, store, [], initial_value=1.0)

    with pytest.raises(RuntimeError, match="closed"):
        controller.start_next_round()

    peer = _controller(1, store, [], initial_value=2.0)
    controller.set_fitness(1.0)
    peer.set_fitness(2.0)
    controller.close_round()

    with pytest.raises(RuntimeError, match="restored"):
        controller.start_next_round()


def test_winner_checkpoint_rebases_into_deterministic_member_local_next_rounds():
    """One winning controller state produces stable target-specific next rounds."""
    store = RoundStore(population_size=3)
    controllers = [
        _controller(
            rank,
            store,
            [],
            initial_value=float(rank + 1),
            seed=17,
            mutations={"lr": RandomValueMutation()},
        )
        for rank in range(3)
    ]

    for controller, fitness in zip(controllers, [4.0, 1.0, 2.0], strict=True):
        controller.set_fitness(fitness)
    for controller in controllers:
        controller.close_round()

    winner_state = controllers[1].state_dict()
    first_generation = _restored_generation(winner_state, initial_value=99.0, seed=999)
    second_generation = _restored_generation(winner_state, initial_value=-99.0, seed=123)

    first_configs = [controller.get_config() for controller in first_generation]
    second_configs = [controller.get_config() for controller in second_generation]

    assert first_configs == second_configs
    assert first_configs[1] == {"lr": 2.0}
    assert first_configs[0] != first_configs[1]
    assert first_configs[2] != first_configs[1]
    assert first_configs[0] != first_configs[2]
    assert [controller.state_dict()["round_index"] for controller in first_generation] == [1, 1, 1]
    assert [controller.state_dict()["fitness"] for controller in first_generation] == [None, None, None]
    assert all(controller.state_dict()["selected_winner"] is None for controller in first_generation)


def _restored_generation(winner_state, *, initial_value, seed):
    controllers = [
        _controller(
            rank,
            RoundStore(population_size=3),
            [],
            initial_value=initial_value,
            seed=seed,
            mutations={"lr": RandomValueMutation()},
        )
        for rank in range(3)
    ]
    for controller in controllers:
        controller.load_state_dict(winner_state)
        controller.start_next_round()
    return controllers


def test_incomplete_population_crashes_before_selection():
    store = RoundStore(population_size=3)
    winner_calls = []
    controller = _controller(0, store, winner_calls, initial_value=1.0)
    peer = _controller(1, store, [], initial_value=2.0)
    controller.set_fitness(1.0)
    peer.set_fitness(2.0)
    state = controller.state_dict()

    with pytest.raises(RuntimeError, match="incomplete"):
        controller.close_round()

    assert winner_calls == []
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
    winner_calls = []
    controller = ClanController(
        member_id=0,
        population_size=3,
        initial_config={"lr": 1.0},
        mutations={"lr": _mutation()},
        mode="min",
        seed=7,
        save_member_fitness=lambda round_: None,
        load_population=lambda round_index: rounds,
        select_winner=winner_calls.append,
    )

    with pytest.raises(RuntimeError, match=message):
        controller.close_round()

    assert winner_calls == []
