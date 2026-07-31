import math

import pytest

from clan_based_tuning import ClanController


class FitnessExchange:
    def __init__(self, population):
        self.population = list(population)
        self.calls = []

    def __call__(self, local_fitness):
        self.calls.append(local_fitness)
        return list(self.population)


class MetadataCheckpoint:
    def __init__(self, metadata=None):
        self.metadata = dict(metadata or {})
        self.updates = []

    def update_metadata(self, metadata):
        self.updates.append(metadata)
        self.metadata.update(metadata)


def _controller(member_id, population, *, mode="min", genome=None):
    exchange = FitnessExchange(population)
    controller = ClanController(
        member_id=member_id,
        population_size=len(population),
        mode=mode,
        genome={"lr": 0.001 * (member_id + 1)} if genome is None else genome,
        exchange_fitness=exchange,
    )
    return controller, exchange


def test_population_resolves_one_checkpoint_source():
    population = [4.0, 1.0, 2.0]
    controllers_and_exchanges = [
        _controller(member_id, population) for member_id in range(len(population))
    ]

    for (controller, _), fitness in zip(controllers_and_exchanges, population, strict=True):
        controller.set_fitness(fitness)

    assert [controller.should_save_checkpoint() for controller, _ in controllers_and_exchanges] == [
        False,
        True,
        False,
    ]
    assert [exchange.calls for _, exchange in controllers_and_exchanges] == [
        [4.0],
        [1.0],
        [2.0],
    ]


def test_max_mode_breaks_ties_by_lower_member_id():
    population = [5.0, 5.0, 2.0]
    controllers = [
        _controller(member_id, population, mode="max")[0] for member_id in range(len(population))
    ]

    for controller, fitness in zip(controllers, population, strict=True):
        controller.set_fitness(fitness)

    assert [controller.should_save_checkpoint() for controller in controllers] == [
        True,
        False,
        False,
    ]


def test_should_save_checkpoint_is_one_collective_decision():
    controller, exchange = _controller(1, [3.0, 1.0, 2.0])
    controller.set_fitness(1.0)

    assert controller.should_save_checkpoint() is True
    assert controller.should_save_checkpoint() is True
    assert exchange.calls == [1.0]


def test_winner_saves_its_copied_genome_without_another_collective():
    genome = {"lr": 0.003, "weight_decay": 0.1}
    controller, exchange = _controller(1, [3.0, 1.0, 2.0], genome=genome)
    genome["lr"] = 9.0
    controller.set_fitness(1.0)
    assert controller.should_save_checkpoint() is True

    checkpoint = MetadataCheckpoint({"lightning": {"format": "ckpt"}})
    returned = controller.save_genome(checkpoint)

    assert returned is checkpoint
    assert exchange.calls == [1.0]
    assert checkpoint.metadata == {
        "lightning": {"format": "ckpt"},
        "clan_based_tuning": {
            "schema_version": 1,
            "member_id": 1,
            "genome": {"lr": 0.003, "weight_decay": 0.1},
        },
    }


def test_save_genome_requires_a_resolved_winning_decision():
    unresolved, unresolved_exchange = _controller(0, [1.0, 2.0])
    unresolved_checkpoint = MetadataCheckpoint()

    with pytest.raises(RuntimeError, match="resolved"):
        unresolved.save_genome(unresolved_checkpoint)

    assert unresolved_exchange.calls == []
    assert unresolved_checkpoint.updates == []

    loser, loser_exchange = _controller(1, [1.0, 2.0])
    loser.set_fitness(2.0)
    assert loser.should_save_checkpoint() is False
    loser_checkpoint = MetadataCheckpoint()

    with pytest.raises(RuntimeError, match="selected"):
        loser.save_genome(loser_checkpoint)

    assert loser_exchange.calls == [2.0]
    assert loser_checkpoint.updates == []


def test_fitness_must_be_set_before_collective_resolution():
    controller, exchange = _controller(0, [1.0, 2.0])

    with pytest.raises(RuntimeError, match="fitness"):
        controller.should_save_checkpoint()

    assert exchange.calls == []


@pytest.mark.parametrize("fitness", [math.nan, math.inf, -math.inf])
def test_nonfinite_fitness_is_rejected_before_collective(fitness):
    controller, exchange = _controller(0, [1.0, 2.0])

    with pytest.raises(ValueError, match="finite"):
        controller.set_fitness(fitness)

    assert exchange.calls == []


def test_fitness_cannot_change_after_assignment():
    controller, exchange = _controller(0, [1.0, 2.0])
    controller.set_fitness(1.0)

    with pytest.raises(RuntimeError, match="already"):
        controller.set_fitness(0.5)

    assert exchange.calls == []


def test_collective_must_return_the_configured_population():
    controller = ClanController(
        member_id=0,
        population_size=3,
        mode="min",
        genome={"lr": 0.001},
        exchange_fitness=lambda local_fitness: [local_fitness, 2.0],
    )
    controller.set_fitness(1.0)

    with pytest.raises(RuntimeError, match="population"):
        controller.should_save_checkpoint()


def test_controller_exposes_no_evolution_or_serialization_api():
    controller, _ = _controller(0, [1.0, 2.0])

    assert not hasattr(controller, "advance")
    assert not hasattr(controller, "get_config")
    assert not hasattr(controller, "genome")
    assert not hasattr(controller, "get_genome")
    assert not hasattr(controller, "state_dict")
    assert not hasattr(controller, "load_state_dict")
