import math

import pytest

from clan_based_tuning.evolution import _MutationRule, select_winner_id


class FixedRandom:
    def __init__(self, displacement):
        self.displacement = displacement

    def gauss(self, mean, standard_deviation):
        return self.displacement


def _rule(**overrides):
    config = {
        "standard_deviation": 0.2,
        "geometry": "linear",
        "minimum": 0.0,
        "maximum": 3.0,
    }
    config.update(overrides)
    return _MutationRule.from_config(config)


def test_mutation_rules_apply_linear_log_and_bounds():
    linear = _rule()
    logarithmic = _rule(geometry="log", minimum=0.1, maximum=20.0)

    assert linear.mutate(2.0, FixedRandom(0.3)) == 2.3
    assert linear.mutate(2.9, FixedRandom(0.3)) == 3.0
    assert logarithmic.mutate(2.0, FixedRandom(math.log(2.0))) == pytest.approx(4.0)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (
            {"geometry": "linear", "minimum": 0.0, "maximum": 1.0},
            "missing required keys",
        ),
        (
            {
                "standard_deviation": 0.2,
                "geometry": "linear",
                "minimum": 0.0,
                "maximum": 1.0,
                "mystery": 3,
            },
            "unknown keys",
        ),
        (
            {
                "standard_deviation": -0.1,
                "geometry": "linear",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "non-negative",
        ),
        (
            {
                "standard_deviation": 0.2,
                "geometry": "quadratic",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "geometry",
        ),
        (
            {
                "standard_deviation": 0.2,
                "geometry": "linear",
                "minimum": 2.0,
                "maximum": 1.0,
            },
            "minimum",
        ),
        (
            {
                "standard_deviation": 0.2,
                "geometry": "log",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "positive minimum",
        ),
    ],
)
def test_mutation_dictionary_is_validated_at_configuration_time(config, message):
    with pytest.raises(ValueError, match=message):
        _MutationRule.from_config(config)


def test_log_mutation_rejects_nonpositive_source_value():
    mutation = _rule(geometry="log", minimum=0.1, maximum=20.0)

    with pytest.raises(ValueError, match="positive source"):
        mutation.mutate(0.0, FixedRandom(0.0))


def test_selection_rule_supports_min_max_and_stable_ties():
    assert select_winner_id([4.0, 1.0, 2.0], "min") == 1
    assert select_winner_id([5.0, 5.0, 2.0], "max") == 0
