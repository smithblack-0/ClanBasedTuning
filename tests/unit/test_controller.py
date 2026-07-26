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
        select_winner=winner_calls.append,
    )


def test_fake_processes_publish_select_and_advance_one_local_round():
    """Each process publishes one round and independently applies the same winner."""
    store = RoundStore(population_size=3)
    winner_calls = [[], [], []]
    controllers = [
        _controller(rank, store, winner_calls[rank], initial_value=float(rank + 1))
        for rank in range(3)
    ]

    for controller, fitness in zip(controllers, [4.0, 1.0, 2.0], strict=True):
        controller.set_fitness(fitness)
    for controller in controllers:
        controller.advance()

    assert winner_calls == [[1], [1], [1]]
    assert [controller.get_config() for controller in controllers] == [
        {"lr": 2.0},
        {"lr": 2.0},
        {"lr": 2.0},
    ]

    controllers[0].set_fitness(3.0)
    assert store.saved[(1, 0)].fitness == 3.0


def test_max_mode_breaks_ties_by_lower_member_id():
    """Every process reaches the same stable winner when best fitness ties."""
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
    for controller in controllers:
        controller.advance()

    assert winner_calls == [[0], [0], [0]]


def test_incomplete_population_crashes_before_winner_transfer():
    """A missing member cannot create a next round or transfer external state."""
    store = RoundStore(population_size=3)
    winner_calls = []
    controller = _controller(0, store, winner_calls, initial_value=1.0)
    peer = _controller(1, store, [], initial_value=2.0)
    controller.set_fitness(1.0)
    peer.set_fitness(2.0)
    state = controller.state_dict()

    with pytest.raises(RuntimeError, match="incomplete"):
        controller.advance()

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
        controller.advance()

    assert winner_calls == []


def test_random_and_current_round_state_resume_together():
    """Restoring one controller reproduces its local next-round mutation."""
    saved_rounds = [
        ClanRound(0, 0, {"lr": 2.0}, lambda round_: None, 0.0),
        ClanRound(1, 0, {"lr": 5.0}, lambda round_: None, 1.0),
    ]
    first_calls = []
    second_calls = []
    first = ClanController(
        member_id=1,
        population_size=2,
        initial_config={"lr": 9.0},
        mutations={"lr": _mutation(standard_deviation=0.5)},
        mode="min",
        seed=17,
        save_member_fitness=lambda round_: None,
        load_population=lambda round_index: saved_rounds,
        select_winner=first_calls.append,
    )
    second = ClanController(
        member_id=1,
        population_size=2,
        initial_config={"lr": 0.0},
        mutations={"lr": _mutation(standard_deviation=0.5)},
        mode="min",
        seed=999,
        save_member_fitness=lambda round_: None,
        load_population=lambda round_index: saved_rounds,
        select_winner=second_calls.append,
    )

    second.load_state_dict(first.state_dict())
    first.advance()
    second.advance()

    assert first_calls == second_calls == [0]
    assert first.get_config() == second.get_config()
