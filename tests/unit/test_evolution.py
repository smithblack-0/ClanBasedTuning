"""Unit contracts for framework-independent Clan selection and mutation policy.

These tests exercise the algorithm without Ray or Lightning. They verify stable winner
selection, mutation validation, and the defining generation contract: every next member is
an independent mutation of the same selected parent in stable member-ID order.
"""

import math
import random
from typing import Any

import pytest

from clan_based_tuning.evolution import (
    build_mutation_rule,
    build_mutation_rules,
    resolve_generation,
    select_winner_id,
)


class FixedRandom:
    """Deterministic Gaussian source used to isolate mutation geometry."""

    def __init__(self, displacement: float) -> None:
        self.displacement = displacement

    def gauss(self, mean: float, standard_deviation: float) -> float:
        """Return the configured displacement regardless of distribution parameters."""

        del mean, standard_deviation
        return self.displacement


def _rule_config(**overrides: Any) -> dict[str, Any]:
    config = {
        "standard_deviation": 0.2,
        "geometry": "linear",
        "minimum": 0.0,
        "maximum": 3.0,
    }
    config.update(overrides)
    return config


def test_mutation_rules_apply_linear_log_and_bounds() -> None:
    """Normalized rules preserve additive/log geometry and inclusive clipping."""

    linear = build_mutation_rule(_rule_config())
    logarithmic = build_mutation_rule(_rule_config(geometry="log", minimum=0.1, maximum=20.0))

    assert linear.mutate(2.0, FixedRandom(0.3)) == 2.3
    assert linear.mutate(2.9, FixedRandom(0.3)) == 3.0
    assert logarithmic.mutate(2.0, FixedRandom(math.log(2.0))) == pytest.approx(4.0)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"geometry": "linear", "minimum": 0.0, "maximum": 1.0}, "missing required keys"),
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
        (_rule_config(standard_deviation=-0.1), "non-negative"),
        (_rule_config(geometry="quadratic"), "geometry"),
        (_rule_config(minimum=2.0, maximum=1.0), "minimum"),
        (_rule_config(geometry="log", minimum=0.0), "positive minimum"),
    ],
)
def test_mutation_dictionary_fails_at_configuration_time(
    config: dict[str, Any],
    message: str,
) -> None:
    """Malformed public mutation dictionaries fail before a Tune run begins."""

    with pytest.raises(ValueError, match=message):
        build_mutation_rule(config)


def test_generation_mutates_every_sibling_from_one_parent_in_stable_order() -> None:
    """Seeded sibling configs are reproducible and include a mutation of the prior winner."""

    mutations = build_mutation_rules(
        {
            "lr": {
                "standard_deviation": 0.15,
                "geometry": "log",
                "minimum": 0.02,
                "maximum": 0.5,
            }
        }
    )
    decision = resolve_generation(
        fitnesses=[1.0, 0.5],
        configs=[{"lr": 0.1}, {"lr": 0.2}],
        mode="min",
        mutations=mutations,
        random_stream=random.Random(7),
    )

    assert decision.winner_id == 1
    assert decision.parent_config == {"lr": 0.2}
    assert [child["lr"] for child in decision.child_configs] == pytest.approx(
        [0.1924690426284743, 0.2159468026720305]
    )


def test_selection_supports_min_max_and_stable_ties() -> None:
    """Both optimization directions resolve exact ties to the lower member ID."""

    assert select_winner_id([4.0, 1.0, 2.0], "min") == 1
    assert select_winner_id([5.0, 5.0, 2.0], "max") == 0


def test_selection_rejects_empty_and_nonfinite_populations() -> None:
    """Selection fails before producing a winner from invalid comparison input."""

    with pytest.raises(ValueError, match="at least one"):
        select_winner_id([], "min")
    with pytest.raises(ValueError, match="finite"):
        select_winner_id([1.0, math.inf], "min")
