import copy
import math

import pytest

from clan_based_tuning import ClanController


def _controller(*, mode="min", seed=7, hyperparameters=None):
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
    return ClanController(hyperparameters=hyperparameters, mode=mode, seed=seed)


def test_initial_configurations_keep_rank_zero_at_defaults():
    """Pre: valid policy and three ranks. Post: rank zero is exact; outputs are separate."""
    configurations = _controller().initial_configurations(3)

    assert configurations[0] == {"lr": 1.0}
    assert len(configurations) == 3
    assert len({id(configuration) for configuration in configurations}) == 3


def test_equal_seed_and_calls_produce_equal_initial_configurations():
    """Pre: equal policies and seeds. Post: redundant controllers produce equal output."""
    first = _controller(seed=13)
    second = _controller(seed=13)

    assert first.initial_configurations(4) == second.initial_configurations(4)


def test_next_generation_minimizes_fitness_and_retains_parent():
    """Pre: complete rank-aligned input. Post: lowest-fitness rank is retained exactly."""
    controller = _controller()
    configurations = [{"lr": 1.0}, {"lr": 2.0}, {"lr": 3.0}]

    parent_rank, next_configurations = controller.next_generation([4.0, 1.0, 2.0], configurations)

    assert parent_rank == 1
    assert next_configurations[1] == {"lr": 2.0}
    assert next_configurations[1] is not configurations[1]


def test_next_generation_maximizes_and_breaks_ties_by_lowest_rank():
    """Pre: two equal best scores in max mode. Post: the lower rank wins."""
    controller = _controller(mode="max")

    parent_rank, _ = controller.next_generation(
        [3.0, 3.0, 1.0],
        [{"lr": 1.0}, {"lr": 2.0}, {"lr": 3.0}],
    )

    assert parent_rank == 0


def test_linear_mutation_adds_gaussian_displacement(monkeypatch):
    """Pre: linear policy and known draw. Post: mutation adds the draw in value units."""
    controller = _controller()
    calls = []

    def draw(mean, standard_deviation):
        calls.append((mean, standard_deviation))
        return 0.3

    monkeypatch.setattr(controller._random, "gauss", draw)

    _, next_configurations = controller.next_generation(
        [0.0, 1.0],
        [{"lr": 2.0}, {"lr": 4.0}],
    )

    assert next_configurations == [{"lr": 2.0}, {"lr": 2.3}]
    assert calls == [(0.0, 0.2)]


def test_log_mutation_multiplies_by_exponential_draw(monkeypatch):
    """Pre: log policy and known draw. Post: mutation multiplies by exp(draw)."""
    controller = _controller(
        hyperparameters={
            "lr": {
                "default": 2.0,
                "standard_deviation": 0.5,
                "geometry": "log",
                "minimum": 0.1,
                "maximum": 20.0,
            }
        }
    )
    monkeypatch.setattr(controller._random, "gauss", lambda mean, std: math.log(2.0))

    _, next_configurations = controller.next_generation(
        [0.0, 1.0],
        [{"lr": 2.0}, {"lr": 4.0}],
    )

    assert next_configurations == [{"lr": 2.0}, {"lr": pytest.approx(4.0)}]


def test_mutation_clamps_to_declared_bounds(monkeypatch):
    """Pre: draw proposes an illegal value. Post: result equals the nearest bound."""
    controller = _controller()
    monkeypatch.setattr(controller._random, "gauss", lambda mean, std: 50.0)

    _, next_configurations = controller.next_generation(
        [0.0, 1.0],
        [{"lr": 2.0}, {"lr": 4.0}],
    )

    assert next_configurations[1] == {"lr": 10.0}


def test_invalid_generation_does_not_advance_random_state():
    """Pre: malformed input. Post: failure occurs before the random stream advances."""
    controller = _controller()
    before = controller.state_dict()

    with pytest.raises(ValueError, match="equal length"):
        controller.next_generation([1.0, 2.0], [{"lr": 1.0}])

    assert controller.state_dict() == before


def test_generation_rejects_nonfinite_fitness():
    """Pre: one nonfinite score. Post: no parent or next configuration is produced."""
    controller = _controller()

    with pytest.raises(ValueError, match="must be finite"):
        controller.next_generation(
            [1.0, float("nan")],
            [{"lr": 1.0}, {"lr": 2.0}],
        )


def test_generation_rejects_wrong_hyperparameter_set():
    """Pre: one configuration omits a declared key. Post: the input is rejected."""
    controller = _controller()

    with pytest.raises(ValueError, match="exactly the declared"):
        controller.next_generation([1.0, 2.0], [{"lr": 1.0}, {}])


def test_generation_rejects_out_of_bounds_configuration():
    """Pre: one current value violates bounds. Post: the input is rejected."""
    controller = _controller()

    with pytest.raises(ValueError, match="must be within"):
        controller.next_generation([1.0, 2.0], [{"lr": 1.0}, {"lr": 20.0}])


def test_inputs_are_not_modified():
    """Pre: mutable caller-owned inputs. Post: successful evolution leaves them unchanged."""
    controller = _controller()
    fitnesses = [1.0, 2.0]
    configurations = [{"lr": 1.0}, {"lr": 2.0}]
    expected_fitnesses = copy.deepcopy(fitnesses)
    expected_configurations = copy.deepcopy(configurations)

    controller.next_generation(fitnesses, configurations)

    assert fitnesses == expected_fitnesses
    assert configurations == expected_configurations


def test_random_state_round_trip_reproduces_next_mutation():
    """Pre: saved state and equal policy. Post: restoration repeats the next result."""
    first = _controller(seed=17)
    second = _controller(seed=999)
    state = first.state_dict()
    second.load_state_dict(state)
    generation = ([0.0, 1.0], [{"lr": 1.0}, {"lr": 2.0}])

    assert first.next_generation(*generation) == second.next_generation(*generation)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("standard_deviation", 0.0, "must be positive"),
        ("geometry", "quadratic", "must be 'linear' or 'log'"),
        ("minimum", 2.0, "must be less than maximum"),
    ],
)
def test_constructor_rejects_invalid_hyperparameter_policy(field, value, message):
    """Pre: one invalid policy field. Post: construction fails before state exists."""
    specification = {
        "default": 1.0,
        "standard_deviation": 0.2,
        "geometry": "linear",
        "minimum": 0.1,
        "maximum": 2.0,
    }
    specification[field] = value

    with pytest.raises(ValueError, match=message):
        _controller(hyperparameters={"lr": specification})
