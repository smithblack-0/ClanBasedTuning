import math

import pytest

from clan_based_tuning import ClanRound, MutationSpec


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


def test_clan_round_carries_config_and_publishes_itself():
    saved = []
    config = {"lr": 1.0}
    round_ = ClanRound(
        member_id=2,
        round_index=4,
        config=config,
        save_member_fitness=saved.append,
    )
    config["lr"] = 9.0

    round_.set_fitness(0.4)

    assert round_.get_config() == {"lr": 1.0}
    assert round_.fitness == 0.4
    assert saved == [round_]


def test_clan_round_rejects_nonfinite_fitness_before_publish():
    saved = []
    round_ = ClanRound(0, 0, {"lr": 1.0}, saved.append)

    with pytest.raises(ValueError, match="finite"):
        round_.set_fitness(math.nan)

    assert saved == []
