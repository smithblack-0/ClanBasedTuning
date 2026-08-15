"""Unit contracts for framework-independent Clan selection and mutation policy.

These tests exercise the algorithm without Ray or Lightning. They verify stable winner
selection, mutation validation, injected composition, and the defining generation contract:
every next member is an independent mutation of the same selected parent in stable member-ID
order.
"""

import math
import random
from collections.abc import Sequence
from typing import Any

import pytest

from clan_based_tuning.evolution import build_mutation_rule, resolve_generation, select_winner_id


class FixedRandom:
    """Expose a fixed displacement so geometry can be tested independently of RNG behavior."""

    def __init__(self, displacement: float) -> None:
        self.displacement = displacement

    def gauss(self, mean: float, standard_deviation: float) -> float:
        """Satisfy the mutation RNG protocol while deliberately ignoring distribution inputs."""

        del mean, standard_deviation
        return self.displacement


def _rule_config(**overrides: Any) -> dict[str, Any]:
    """Keep valid-rule boilerplate out of tests that each vary one contract dimension."""

    config = {
        "standard_deviation": 0.2,
        "geometry": "linear",
        "minimum": 0.0,
        "maximum": 3.0,
    }
    config.update(overrides)
    return config


def test_mutation_rules_apply_linear_log_and_bounds() -> None:
    """Linear/log geometry and post-mutation clipping remain distinct behaviors."""

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
    """Invalid search-space declarations fail before any generation transition can run."""

    with pytest.raises(ValueError, match=message):
        build_mutation_rule(config)


def test_generation_mutates_every_sibling_from_one_parent_in_stable_order() -> None:
    """Seeded siblings remain tied to member order and include a mutation of the prior winner."""

    mutations = {
        "lr": build_mutation_rule(
            {
                "standard_deviation": 0.15,
                "geometry": "log",
                "minimum": 0.02,
                "maximum": 0.5,
            }
        )
    }
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


def test_generation_uses_injected_winner_selection() -> None:
    """Generation composition can isolate winner policy without replacing framework state."""

    selections: list[tuple[list[float], str]] = []

    def select_first(population: Sequence[float], mode: str) -> int:
        """Force member zero while recording the exact policy inputs passed by orchestration."""

        selections.append((list(population), mode))
        return 0

    decision = resolve_generation(
        fitnesses=[9.0, 1.0],
        configs=[{"lr": 0.1}, {"lr": 0.2}],
        mode="min",
        mutations={},
        random_stream=random.Random(7),
        _select_winner=select_first,
    )

    assert selections == [([9.0, 1.0], "min")]
    assert decision.winner_id == 0
    assert decision.parent_config == {"lr": 0.1}
    assert decision.child_configs == ({"lr": 0.1}, {"lr": 0.1})


def test_selection_supports_min_max_and_stable_ties() -> None:
    """Both optimization directions use the same deterministic lower-member tie break."""

    assert select_winner_id([4.0, 1.0, 2.0], "min") == 1
    assert select_winner_id([5.0, 5.0, 2.0], "max") == 0


def test_selection_rejects_empty_and_nonfinite_populations() -> None:
    """Undefined comparison populations cannot produce a parent decision."""

    with pytest.raises(ValueError, match="at least one"):
        select_winner_id([], "min")
    with pytest.raises(ValueError, match="finite"):
        select_winner_id([1.0, math.inf], "min")
