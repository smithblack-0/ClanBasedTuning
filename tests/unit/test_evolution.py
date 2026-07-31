import math

import pytest

from clan_based_tuning import MutationSpec
from clan_based_tuning.evolution import select_winner_id


class FixedRandom:
    def __init__(self, displacement):
        self.displacement = displacement

    def gauss(self, mean, standard_deviation):
        return self.displacement


def test_mutation_spec_applies_linear_and_log_rules():
    linear = MutationSpec(
        standard_deviation=0.2,
        geometry="linear",
        minimum=0.0,
        maximum=3.0,
    )
    logarithmic = MutationSpec(
        standard_deviation=0.2,
        geometry="log",
        minimum=0.1,
        maximum=20.0,
    )

    assert linear.mutate(2.0, FixedRandom(0.3)) == 2.3
    assert linear.mutate(2.9, FixedRandom(0.3)) == 3.0
    assert logarithmic.mutate(2.0, FixedRandom(math.log(2.0))) == pytest.approx(4.0)


def test_unknown_mutation_geometry_crashes_when_used():
    mutation = MutationSpec(
        standard_deviation=0.2,
        geometry="quadratic",
        minimum=0.0,
        maximum=3.0,
    )

    with pytest.raises(ValueError, match="unknown mutation geometry"):
        mutation.mutate(2.0, FixedRandom(0.3))


def test_selection_rule_supports_min_max_and_stable_ties():
    assert select_winner_id([4.0, 1.0, 2.0], "min") == 1
    assert select_winner_id([5.0, 5.0, 2.0], "max") == 0
