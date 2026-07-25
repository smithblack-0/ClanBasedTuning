from __future__ import annotations

import math
import random

import pytest

from clan_based_tuning.controller import ClanController


def _parameters() -> dict[str, dict[str, float | str]]:
    return {
        "lr": {
            "default": 0.01,
            "std": 0.25,
            "sampling": "log",
            "lower": 0.001,
            "upper": 0.1,
        },
        "weight_decay": {
            "default": 0.02,
            "std": 0.01,
            "sampling": "linear",
            "lower": 0.0,
            "upper": 0.1,
        },
    }


def _controller(
    *,
    mode: str = "min",
    population_size: int = 3,
    parameters: dict[str, dict[str, float | str]] | None = None,
) -> ClanController:
    return ClanController(
        population_size=population_size,
        parameters=_parameters() if parameters is None else parameters,
        mode=mode,
    )


def _population() -> dict[str, dict[str, object]]:
    return {
        "trial-c": {"fitness": 0.8, "config": {"lr": 0.03, "weight_decay": 0.03}},
        "trial-a": {"fitness": 0.2, "config": {"lr": 0.01, "weight_decay": 0.01}},
        "trial-b": {"fitness": 0.5, "config": {"lr": 0.02, "weight_decay": 0.02}},
    }


def test_initialize_keeps_one_exact_default_and_emits_complete_population():
    configs = _controller().initialize(["trial-c", "trial-a", "trial-b"], seed=17)

    assert list(configs) == ["trial-a", "trial-b", "trial-c"]
    assert configs["trial-a"] == {"lr": 0.01, "weight_decay": 0.02}
    assert configs["trial-b"] != configs["trial-a"]
    assert configs["trial-c"] != configs["trial-a"]
    for config in configs.values():
        assert 0.001 <= config["lr"] <= 0.1
        assert 0.0 <= config["weight_decay"] <= 0.1


def test_linear_mutation_is_additive_in_ordinary_coordinates():
    parameters = {
        "momentum": {
            "default": 0.5,
            "std": 0.1,
            "sampling": "linear",
            "lower": 0.0,
            "upper": 1.0,
        }
    }
    expected = 0.5 + random.Random(3).gauss(0.0, 0.1)

    configs = _controller(population_size=2, parameters=parameters).initialize(
        ["a", "b"], seed=3
    )

    assert configs["b"]["momentum"] == pytest.approx(expected)


def test_log_mutation_is_multiplicative_in_ordinary_coordinates():
    parameters = {
        "lr": {
            "default": 0.01,
            "std": 0.2,
            "sampling": "log",
            "lower": 1e-5,
            "upper": 1.0,
        }
    }
    displacement = random.Random(5).gauss(0.0, 0.2)

    configs = _controller(population_size=2, parameters=parameters).initialize(
        ["a", "b"], seed=5
    )

    assert configs["b"]["lr"] == pytest.approx(0.01 * math.exp(displacement))


def test_mutations_are_constrained_to_declared_bounds():
    parameters = {
        "linear": {
            "default": 0.5,
            "std": 10.0,
            "sampling": "linear",
            "lower": 0.0,
            "upper": 1.0,
        },
        "log": {
            "default": 1.0,
            "std": 10.0,
            "sampling": "log",
            "lower": 0.5,
            "upper": 2.0,
        },
    }

    configs = _controller(population_size=2, parameters=parameters).initialize(
        ["a", "b"], seed=0
    )

    assert 0.0 <= configs["b"]["linear"] <= 1.0
    assert 0.5 <= configs["b"]["log"] <= 2.0


def test_advance_selects_sole_parent_and_emits_complete_next_population():
    parent_id, configs = _controller().advance(_population(), seed=19)

    assert parent_id == "trial-a"
    assert set(configs) == {"trial-a", "trial-b", "trial-c"}
    assert configs["trial-a"] == {"lr": 0.01, "weight_decay": 0.01}
    assert configs["trial-b"] != configs["trial-a"]
    assert configs["trial-c"] != configs["trial-a"]


def test_max_mode_and_ties_use_stable_member_identity():
    population = {
        "trial-z": {"fitness": 1.0, "config": {"lr": 0.01, "weight_decay": 0.01}},
        "trial-a": {"fitness": 1.0, "config": {"lr": 0.02, "weight_decay": 0.02}},
    }

    parent_id, configs = _controller(mode="max", population_size=2).advance(
        population, seed=3
    )

    assert parent_id == "trial-a"
    assert configs["trial-a"] == {"lr": 0.02, "weight_decay": 0.02}


def test_redundant_controllers_agree_for_same_inputs_and_seed():
    first = _controller()
    second = _controller(parameters=dict(reversed(_parameters().items())))

    first_result = first.advance(_population(), seed=41)
    second_result = second.advance(dict(reversed(_population().items())), seed=41)

    assert first_result == second_result


def test_operations_do_not_modify_inputs():
    parameters = _parameters()
    population = _population()
    original_parameters = {name: dict(spec) for name, spec in parameters.items()}
    original_population = {
        member_id: {"fitness": result["fitness"], "config": dict(result["config"])}
        for member_id, result in population.items()
    }
    controller = _controller(parameters=parameters)

    controller.initialize(["a", "b", "c"], seed=1)
    controller.advance(population, seed=1)

    assert parameters == original_parameters
    assert population == original_population


@pytest.mark.parametrize(
    ("population", "error", "match"),
    [
        ({}, ValueError, "exactly 3"),
        (
            {"a": {"fitness": 1.0, "config": {"lr": 0.01, "weight_decay": 0.01}}},
            ValueError,
            "exactly 3",
        ),
        (
            {
                "a": {"fitness": math.nan, "config": {"lr": 0.01, "weight_decay": 0.01}},
                "b": {"fitness": 1.0, "config": {"lr": 0.02, "weight_decay": 0.02}},
                "c": {"fitness": 2.0, "config": {"lr": 0.03, "weight_decay": 0.03}},
            },
            ValueError,
            "must be finite",
        ),
        (
            {
                "a": {"fitness": 0.1, "config": {"lr": 0.01, "weight_decay": 0.01}},
                "b": {
                    "fitness": 0.2,
                    "config": {"lr": 0.02, "weight_decay": 0.02},
                    "extra": 1,
                },
                "c": {"fitness": 0.3, "config": {"lr": 0.03, "weight_decay": 0.03}},
            },
            ValueError,
            "exactly 'fitness' and 'config'",
        ),
        (
            {
                "a": {"fitness": 0.1, "config": {"lr": 0.01}},
                "b": {"fitness": 0.2, "config": {"lr": 0.02, "weight_decay": 0.02}},
                "c": {"fitness": 0.3, "config": {"lr": 0.03, "weight_decay": 0.03}},
            },
            ValueError,
            "configured optimizer fields",
        ),
        (
            {
                "a": {"fitness": 0.1, "config": {"lr": 0.5, "weight_decay": 0.01}},
                "b": {"fitness": 0.2, "config": {"lr": 0.02, "weight_decay": 0.02}},
                "c": {"fitness": 0.3, "config": {"lr": 0.03, "weight_decay": 0.03}},
            },
            ValueError,
            "must be within",
        ),
    ],
)
def test_invalid_population_is_rejected(population, error, match):
    with pytest.raises(error, match=match):
        _controller().advance(population, seed=1)


def test_initialization_rejects_incomplete_duplicate_or_invalid_members():
    controller = _controller()

    with pytest.raises(ValueError, match="exactly 3"):
        controller.initialize(["a", "b"], seed=1)
    with pytest.raises(ValueError, match="unique"):
        controller.initialize(["a", "a", "b"], seed=1)
    with pytest.raises(TypeError, match="seed"):
        controller.initialize(["a", "b", "c"], seed=True)


def test_constructor_rejects_invalid_policy():
    with pytest.raises(TypeError, match="population_size"):
        _controller(population_size=True)
    with pytest.raises(ValueError, match="at least two"):
        _controller(population_size=1)
    with pytest.raises(ValueError, match="mode"):
        _controller(mode="median")
    with pytest.raises(ValueError, match="at least one"):
        _controller(parameters={})
    with pytest.raises(ValueError, match="exactly"):
        _controller(parameters={"lr": {"default": 0.1}})

    invalid = _parameters()
    invalid["lr"]["std"] = 0.0
    with pytest.raises(ValueError, match="must be positive"):
        _controller(parameters=invalid)

    invalid = _parameters()
    invalid["lr"]["sampling"] = "uniform"
    with pytest.raises(ValueError, match="must be 'linear' or 'log'"):
        _controller(parameters=invalid)

    invalid = _parameters()
    invalid["lr"]["lower"] = 0.0
    with pytest.raises(ValueError, match="positive lower bound"):
        _controller(parameters=invalid)
