import copy
import math

import pytest

from clan_based_tuning import ClanController, Population


def _controller(*, population_size=3, mode="min", seed=7, hyperparameters=None):
    if hyperparameters is None:
        hyperparameters = {
            "lr": {
                "default": 1.0,
                "standard_deviation": 0.2,
                "geometry": "linear",
                "minimum": 0.1,
                "maximum": 10.0,
            }
        }
    return ClanController(
        population_size=population_size,
        hyperparameters=hyperparameters,
        mode=mode,
        seed=seed,
    )


def _complete_population(controller, fitnesses):
    population = controller.initial_population()
    for rank, fitness in enumerate(fitnesses):
        population.set_fitness(rank, fitness)
    return population


def test_population_copies_and_names_ranked_configuration_contract():
    """Pre: contiguous rank dictionary. Post: Population owns separate configuration copies."""
    configurations = {0: {"lr": 1.0}, 1: {"lr": 2.0}}

    population = Population(configurations)
    configurations[0]["lr"] = 9.0

    assert population.ranks == range(0, 2)
    assert population.get_configuration(0) == {"lr": 1.0}
    assert len(population) == 2


def test_population_rejects_noncontiguous_ranks_at_construction():
    """Pre: malformed outer structure. Post: Population refuses an ambiguous rank contract."""
    with pytest.raises(ValueError, match="contiguous from zero"):
        Population({0: {"lr": 1.0}, 2: {"lr": 2.0}})


def test_population_sets_and_gets_fitness_by_rank():
    """Pre: valid Population and finite score. Post: score is associated with one rank."""
    population = Population({0: {"lr": 1.0}, 1: {"lr": 2.0}})

    population.set_fitness(1, 0.25)

    assert population.get_fitness(1) == 0.25
    assert population.missing_fitness_ranks() == (0,)


def test_population_rejects_unknown_rank_and_nonfinite_fitness():
    """Pre: invalid fitness writes. Post: Population state remains unambiguous."""
    population = Population({0: {"lr": 1.0}, 1: {"lr": 2.0}})

    with pytest.raises(KeyError, match="unknown population rank"):
        population.set_fitness(2, 1.0)
    with pytest.raises(ValueError, match="must be finite"):
        population.set_fitness(0, float("nan"))


def test_initial_population_uses_fixed_size_and_retains_defaults_at_rank_zero():
    """Pre: constructed controller. Post: one complete Population is created without fitness."""
    population = _controller(population_size=3).initial_population()

    assert len(population) == 3
    assert population.get_configuration(0) == {"lr": 1.0}
    assert population.missing_fitness_ranks() == (0, 1, 2)
    assert len({id(configuration) for configuration in population.configurations.values()}) == 3


def test_equal_policy_seed_and_calls_produce_equal_initial_populations():
    """Pre: redundant controllers. Post: their initial configuration dictionaries agree."""
    first = _controller(seed=13)
    second = _controller(seed=13)

    assert first.initial_population().configurations == second.initial_population().configurations


def test_next_generation_requires_population_contract():
    """Pre: arbitrary dictionary. Post: controller rejects data outside the named contract."""
    with pytest.raises(TypeError, match="must be a Population"):
        _controller().next_generation({})


def test_next_generation_requires_controller_population_size():
    """Pre: valid Population from another size. Post: fixed controller policy rejects it."""
    population = Population({0: {"lr": 1.0}, 1: {"lr": 2.0}})
    population.set_fitness(0, 1.0)
    population.set_fitness(1, 2.0)

    with pytest.raises(ValueError, match="exactly 3 ranks"):
        _controller(population_size=3).next_generation(population)


def test_missing_fitness_fails_before_random_state_advances():
    """Pre: one rank has not reported. Post: no transition or random advancement occurs."""
    controller = _controller(population_size=2)
    population = controller.initial_population()
    population.set_fitness(0, 1.0)
    before = controller.state_dict()

    with pytest.raises(RuntimeError, match="missing fitness"):
        controller.next_generation(population)

    assert controller.state_dict() == before


def test_next_generation_minimizes_and_retains_parent_configuration():
    """Pre: complete min-mode Population. Post: best rank is retained in a fresh Population."""
    controller = _controller(population_size=3)
    population = _complete_population(controller, [4.0, 1.0, 2.0])
    expected_parent = population.get_configuration(1)

    parent_rank, next_population = controller.next_generation(population)

    assert parent_rank == 1
    assert isinstance(next_population, Population)
    assert next_population.get_configuration(1) == expected_parent
    assert next_population.missing_fitness_ranks() == (0, 1, 2)


def test_next_generation_maximizes_and_breaks_ties_by_lowest_rank():
    """Pre: equal best scores in max mode. Post: stable lowest-rank tie behavior wins."""
    controller = _controller(population_size=3, mode="max")
    population = _complete_population(controller, [3.0, 3.0, 1.0])

    parent_rank, _ = controller.next_generation(population)

    assert parent_rank == 0


def test_linear_mutation_adds_gaussian_displacement(monkeypatch):
    """Pre: linear policy and known draw. Post: child adds the draw in value units."""
    controller = _controller(population_size=2)
    population = Population({0: {"lr": 2.0}, 1: {"lr": 4.0}})
    population.set_fitness(0, 0.0)
    population.set_fitness(1, 1.0)
    calls = []

    def draw(mean, standard_deviation):
        calls.append((mean, standard_deviation))
        return 0.3

    monkeypatch.setattr(controller._random, "gauss", draw)

    _, next_population = controller.next_generation(population)

    assert next_population.configurations == {0: {"lr": 2.0}, 1: {"lr": 2.3}}
    assert calls == [(0.0, 0.2)]


def test_log_mutation_multiplies_by_exponential_draw(monkeypatch):
    """Pre: log policy and known draw. Post: child multiplies by exp(draw)."""
    controller = _controller(
        population_size=2,
        hyperparameters={
            "lr": {
                "default": 2.0,
                "standard_deviation": 0.5,
                "geometry": "log",
                "minimum": 0.1,
                "maximum": 20.0,
            }
        },
    )
    population = Population({0: {"lr": 2.0}, 1: {"lr": 4.0}})
    population.set_fitness(0, 0.0)
    population.set_fitness(1, 1.0)
    monkeypatch.setattr(controller._random, "gauss", lambda mean, std: math.log(2.0))

    _, next_population = controller.next_generation(population)

    assert next_population.get_configuration(1) == {"lr": pytest.approx(4.0)}


def test_log_mutation_overflow_clamps_to_upper_bound(monkeypatch):
    """Pre: overflowing log draw. Post: bounded policy returns the upper limit."""
    controller = _controller(
        population_size=2,
        hyperparameters={
            "lr": {
                "default": 2.0,
                "standard_deviation": 1.0,
                "geometry": "log",
                "minimum": 0.1,
                "maximum": 20.0,
            }
        },
    )
    population = Population({0: {"lr": 2.0}, 1: {"lr": 4.0}})
    population.set_fitness(0, 0.0)
    population.set_fitness(1, 1.0)
    monkeypatch.setattr(controller._random, "gauss", lambda mean, std: 1000.0)

    _, next_population = controller.next_generation(population)

    assert next_population.get_configuration(1) == {"lr": 20.0}


def test_next_generation_does_not_modify_current_population():
    """Pre: complete mutable Population. Post: transition leaves current generation unchanged."""
    controller = _controller(population_size=2)
    population = _complete_population(controller, [1.0, 2.0])
    expected_configurations = copy.deepcopy(population.configurations)
    expected_fitness = copy.deepcopy(population.fitness)

    controller.next_generation(population)

    assert population.configurations == expected_configurations
    assert population.fitness == expected_fitness


def test_random_state_round_trip_reproduces_next_population():
    """Pre: saved state and equal policy. Post: restoration repeats the next transition."""
    first = _controller(population_size=2, seed=17)
    second = _controller(population_size=2, seed=999)
    population = Population({0: {"lr": 1.0}, 1: {"lr": 2.0}})
    population.set_fitness(0, 0.0)
    population.set_fitness(1, 1.0)
    second.load_state_dict(first.state_dict())

    first_result = first.next_generation(population)
    second_result = second.next_generation(population)

    assert first_result[0] == second_result[0]
    assert first_result[1].configurations == second_result[1].configurations


@pytest.mark.parametrize("population_size", [True, 1, 1.5])
def test_constructor_rejects_invalid_population_size(population_size):
    """Pre: invalid immutable size. Post: construction fails before a policy exists."""
    with pytest.raises((TypeError, ValueError), match="population_size"):
        _controller(population_size=population_size)


@pytest.mark.parametrize("seed", [None, True, 1.5, "17"])
def test_constructor_rejects_noninteger_seed(seed):
    """Pre: ambiguous RNG seed. Post: construction rejects it once at the boundary."""
    with pytest.raises(TypeError, match="seed must be an integer"):
        _controller(seed=seed)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("standard_deviation", 0.0, "must be positive"),
        ("geometry", "quadratic", "must be 'linear' or 'log'"),
        ("minimum", 2.0, "must be less than maximum"),
        ("default", "1.0", "must be a real scalar"),
    ],
)
def test_constructor_rejects_invalid_hyperparameter_policy(field, value, message):
    """Pre: invalid immutable policy field. Post: construction fails before use."""
    specification = {
        "default": 1.0,
        "standard_deviation": 0.2,
        "geometry": "linear",
        "minimum": 0.1,
        "maximum": 2.0,
    }
    specification[field] = value

    with pytest.raises((TypeError, ValueError), match=message):
        _controller(hyperparameters={"lr": specification})
