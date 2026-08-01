import math

import pytest

from clan_based_tuning import ClanController


class PopulationRuntime:
    def __init__(self, population):
        self.population = dict(population)
        self.calls = []

    def resolve(self, local_fitness):
        self.calls.append(local_fitness)
        return dict(self.population)


def _controller(member_id, population, *, mode="min"):
    runtime = PopulationRuntime(population)
    controller = ClanController(
        member_id=member_id,
        population_size=len(population),
        mode=mode,
        population_runtime=runtime,
    )
    return controller, runtime


def test_population_resolves_one_checkpoint_source():
    population = {0: 4.0, 1: 1.0, 2: 2.0}
    controllers_and_runtimes = [
        _controller(member_id, population) for member_id in range(len(population))
    ]

    for (controller, _), fitness in zip(
        controllers_and_runtimes, population.values(), strict=True
    ):
        controller.set_fitness(fitness)

    assert [controller.should_save_checkpoint() for controller, _ in controllers_and_runtimes] == [
        False,
        True,
        False,
    ]
    assert [runtime.calls for _, runtime in controllers_and_runtimes] == [
        [4.0],
        [1.0],
        [2.0],
    ]


def test_member_identity_not_mapping_order_determines_the_winner():
    population = {2: 2.0, 0: 4.0, 1: 1.0}
    controller, _ = _controller(1, population)
    controller.set_fitness(1.0)

    assert controller.should_save_checkpoint() is True


def test_max_mode_breaks_ties_by_lower_member_id():
    population = {0: 5.0, 1: 5.0, 2: 2.0}
    controllers = [
        _controller(member_id, population, mode="max")[0]
        for member_id in range(len(population))
    ]

    for controller, fitness in zip(controllers, population.values(), strict=True):
        controller.set_fitness(fitness)

    assert [controller.should_save_checkpoint() for controller in controllers] == [
        True,
        False,
        False,
    ]


def test_should_save_checkpoint_is_one_population_decision():
    controller, runtime = _controller(1, {0: 3.0, 1: 1.0, 2: 2.0})
    controller.set_fitness(1.0)

    assert controller.should_save_checkpoint() is True
    assert controller.should_save_checkpoint() is True
    assert runtime.calls == [1.0]


def test_fitness_must_be_set_before_population_resolution():
    controller, runtime = _controller(0, {0: 1.0, 1: 2.0})

    with pytest.raises(RuntimeError, match="fitness"):
        controller.should_save_checkpoint()

    assert runtime.calls == []


@pytest.mark.parametrize("fitness", [math.nan, math.inf, -math.inf])
def test_nonfinite_fitness_is_rejected_before_population_resolution(fitness):
    controller, runtime = _controller(0, {0: 1.0, 1: 2.0})

    with pytest.raises(ValueError, match="finite"):
        controller.set_fitness(fitness)

    assert runtime.calls == []


def test_fitness_cannot_change_after_assignment():
    controller, runtime = _controller(0, {0: 1.0, 1: 2.0})
    controller.set_fitness(1.0)

    with pytest.raises(RuntimeError, match="already"):
        controller.set_fitness(0.5)

    assert runtime.calls == []


def test_population_runtime_must_return_every_configured_member():
    controller = ClanController(
        member_id=0,
        population_size=3,
        mode="min",
        population_runtime=PopulationRuntime({0: 1.0, 1: 2.0}),
    )
    controller.set_fitness(1.0)

    with pytest.raises(RuntimeError, match="member set"):
        controller.should_save_checkpoint()


def test_population_runtime_rejects_unconfigured_members():
    controller = ClanController(
        member_id=0,
        population_size=2,
        mode="min",
        population_runtime=PopulationRuntime({0: 1.0, 1: 2.0, 2: 3.0}),
    )
    controller.set_fitness(1.0)

    with pytest.raises(RuntimeError, match="member set"):
        controller.should_save_checkpoint()


def test_population_runtime_must_return_finite_fitness():
    controller = ClanController(
        member_id=0,
        population_size=2,
        mode="min",
        population_runtime=PopulationRuntime({0: 1.0, 1: math.nan}),
    )
    controller.set_fitness(1.0)

    with pytest.raises(RuntimeError, match="non-finite"):
        controller.should_save_checkpoint()


def test_controller_has_no_evolution_genome_or_checkpoint_state_api():
    controller, _ = _controller(0, {0: 1.0, 1: 2.0})

    assert not hasattr(controller, "advance")
    assert not hasattr(controller, "get_config")
    assert not hasattr(controller, "genome")
    assert not hasattr(controller, "get_genome")
    assert not hasattr(controller, "state_dict")
    assert not hasattr(controller, "load_state_dict")
