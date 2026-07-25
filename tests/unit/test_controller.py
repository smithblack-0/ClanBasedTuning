from __future__ import annotations

import math

import pytest

from clan_based_tuning.controller import ClanPopulationPolicy, MemberResult


def _population() -> dict[str, MemberResult]:
    return {
        "trial-c": MemberResult(0.8, {"lr": 0.03, "weight_decay": 0.003, "batch_size": 64}),
        "trial-a": MemberResult(0.2, {"lr": 0.01, "weight_decay": 0.001, "batch_size": 64}),
        "trial-b": MemberResult(0.5, {"lr": 0.02, "weight_decay": 0.002, "batch_size": 64}),
    }


def test_min_policy_selects_parent_and_emits_complete_configs():
    policy = ClanPopulationPolicy(
        mode="min",
        field_factors={"lr": (0.8, 1.2), "weight_decay": (0.5, 2.0)},
    )

    decision = policy.decide(_population(), seed=17)

    assert decision.parent_id == "trial-a"
    assert decision.parent_fitness == pytest.approx(0.2)
    assert set(decision.optimizer_configs) == {"trial-a", "trial-b", "trial-c"}
    assert decision.optimizer_configs["trial-a"] == {
        "lr": 0.01,
        "weight_decay": 0.001,
        "batch_size": 64,
    }
    for member_id in ("trial-b", "trial-c"):
        config = decision.optimizer_configs[member_id]
        lr_factor = config["lr"] / 0.01
        assert lr_factor == pytest.approx(0.8) or lr_factor == pytest.approx(1.2)
        assert (
            config["weight_decay"] / 0.001 == pytest.approx(0.5)
            or config["weight_decay"] / 0.001 == pytest.approx(2.0)
        )
        assert config["batch_size"] == 64
    lr_factors = sorted(
        decision.optimizer_configs[member_id]["lr"] / 0.01
        for member_id in ("trial-b", "trial-c")
    )
    assert lr_factors == pytest.approx([0.8, 1.2])


def test_max_policy_and_ties_use_stable_member_identity():
    policy = ClanPopulationPolicy(mode="max", field_factors={"lr": (0.5, 2.0)})
    population = {
        "trial-z": MemberResult(1.0, {"lr": 0.1}),
        "trial-a": MemberResult(1.0, {"lr": 0.2}),
    }

    decision = policy.decide(population, seed=3)

    assert decision.parent_id == "trial-a"
    assert decision.optimizer_configs["trial-a"] == {"lr": 0.2}


def test_same_input_and_seed_produce_same_decision_without_state():
    policy = ClanPopulationPolicy(mode="min", field_factors={"lr": (0.8, 1.2)})

    first = policy.decide(_population(), seed=41)
    second = policy.decide(dict(reversed(_population().items())), seed=41)

    assert first == second


def test_decision_does_not_modify_input_configurations():
    population = _population()
    original = {
        member_id: dict(result.optimizer_config)
        for member_id, result in population.items()
    }
    policy = ClanPopulationPolicy(mode="min", field_factors={"lr": (0.8, 1.2)})

    policy.decide(population, seed=5)

    current = {
        member_id: dict(result.optimizer_config)
        for member_id, result in population.items()
    }
    assert current == original


@pytest.mark.parametrize(
    ("population", "error", "match"),
    [
        ({}, ValueError, "at least two"),
        (
            {"a": MemberResult(1.0, {"lr": 0.1})},
            ValueError,
            "at least two",
        ),
        (
            {
                "a": MemberResult(math.nan, {"lr": 0.1}),
                "b": MemberResult(1.0, {"lr": 0.2}),
            },
            ValueError,
            r"fitness.*finite",
        ),
    ],
)
def test_invalid_population_is_rejected(population, error, match):
    policy = ClanPopulationPolicy(mode="min", field_factors={"lr": (0.8, 1.2)})

    with pytest.raises(error, match=match):
        policy.decide(population, seed=1)


def test_missing_or_nonnumeric_parent_field_is_rejected():
    missing = {
        "a": MemberResult(0.1, {"weight_decay": 0.01}),
        "b": MemberResult(0.2, {"lr": 0.2}),
    }
    nonnumeric = {
        "a": MemberResult(0.1, {"lr": "fast"}),
        "b": MemberResult(0.2, {"lr": 0.2}),
    }
    policy = ClanPopulationPolicy(mode="min", field_factors={"lr": (0.8, 1.2)})

    with pytest.raises(ValueError, match="missing field 'lr'"):
        policy.decide(missing, seed=1)
    with pytest.raises(TypeError, match=r"field 'lr'.*real scalar"):
        policy.decide(nonnumeric, seed=1)


def test_failure_does_not_change_later_decisions():
    policy = ClanPopulationPolicy(mode="min", field_factors={"lr": (0.8, 1.2)})
    invalid = {
        "a": MemberResult(math.inf, {"lr": 0.1}),
        "b": MemberResult(1.0, {"lr": 0.2}),
    }

    with pytest.raises(ValueError, match=r"fitness.*finite"):
        policy.decide(invalid, seed=11)

    assert policy.decide(_population(), seed=11) == ClanPopulationPolicy(
        mode="min",
        field_factors={"lr": (0.8, 1.2)},
    ).decide(_population(), seed=11)


def test_policy_configuration_rejects_ambiguous_or_invalid_scaling():
    with pytest.raises(ValueError, match="mode"):
        ClanPopulationPolicy(mode="median", field_factors={"lr": (0.8,)})
    with pytest.raises(ValueError, match="at least one optimizer field"):
        ClanPopulationPolicy(mode="min", field_factors={})
    with pytest.raises(ValueError, match="must change the value"):
        ClanPopulationPolicy(mode="min", field_factors={"lr": (1.0,)})
    with pytest.raises(ValueError, match="finite and positive"):
        ClanPopulationPolicy(mode="min", field_factors={"lr": (0.0,)})
