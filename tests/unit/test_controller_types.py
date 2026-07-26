import math
import random

import pytest

from clan_based_tuning import (
    ControllerPolicy,
    MutationSpec,
    Population,
    PopulationMember,
)


def _mutation(**changes):
    values = {
        "default": 1.0,
        "standard_deviation": 0.2,
        "geometry": "linear",
        "minimum": 0.1,
        "maximum": 10.0,
    }
    values.update(changes)
    return MutationSpec(**values)


def test_mutation_spec_owns_its_numeric_semantics():
    """Pre: invalid local mutation rules. Post: each rule rejects its own defect."""
    with pytest.raises(ValueError, match="positive"):
        _mutation(standard_deviation=0.0)
    with pytest.raises(ValueError, match="geometry"):
        _mutation(geometry="quadratic")
    with pytest.raises(ValueError, match="less than"):
        _mutation(minimum=2.0, maximum=1.0)


def test_mutation_spec_applies_linear_and_log_rules(monkeypatch):
    """Pre: known draws. Post: each spec applies its documented local geometry."""
    stream = random.Random(1)
    linear = _mutation()
    monkeypatch.setattr(stream, "gauss", lambda mean, std: 0.3)
    assert linear.mutate(2.0, stream) == 2.3

    logarithmic = _mutation(
        default=2.0,
        geometry="log",
        minimum=0.1,
        maximum=20.0,
    )
    monkeypatch.setattr(stream, "gauss", lambda mean, std: math.log(2.0))
    assert logarithmic.mutate(2.0, stream) == pytest.approx(4.0)
    monkeypatch.setattr(stream, "gauss", lambda mean, std: 1000.0)
    assert logarithmic.mutate(2.0, stream) == 20.0


def test_controller_policy_composes_mutation_specs():
    """Pre: fixed policy settings. Post: policy owns a copied mutation mapping."""
    mutations = {"lr": _mutation()}
    policy = ControllerPolicy(3, mutations, "min", 7)
    mutations["weight_decay"] = _mutation()

    assert policy.population_size == 3
    assert tuple(policy.mutations) == ("lr",)


def test_controller_policy_rejects_only_direct_policy_defects():
    """Pre: invalid immediate fields. Post: policy rejects them without deep parsing."""
    with pytest.raises(ValueError, match="at least two"):
        ControllerPolicy(1, {"lr": _mutation()}, "min", 7)
    with pytest.raises(ValueError, match="non-empty"):
        ControllerPolicy(2, {}, "min", 7)
    with pytest.raises(ValueError, match="mode"):
        ControllerPolicy(2, {"lr": _mutation()}, "middle", 7)
    with pytest.raises(TypeError, match="MutationSpec"):
        ControllerPolicy(2, {"lr": object()}, "min", 7)


def test_population_member_means_values_plus_optional_fitness():
    """Pre: member data. Post: values are copied and finite fitness is recorded."""
    values = {"lr": 1.0}
    member = PopulationMember(values)
    values["lr"] = 9.0
    member.set_fitness(0.4)

    assert member.hyperparameters == {"lr": 1.0}
    assert member.fitness == 0.4
    with pytest.raises(ValueError, match="finite"):
        member.set_fitness(math.nan)


def test_population_composes_members_by_contiguous_rank():
    """Pre: rank-to-member dictionary. Post: one stable population is constructed."""
    population = Population(
        {
            0: PopulationMember({"lr": 1.0}),
            1: PopulationMember({"lr": 2.0}),
        }
    )

    population.set_fitness(1, 0.25)

    assert population.ranks == range(0, 2)
    assert population.members[1].fitness == 0.25
    assert population.missing_fitness_ranks() == (0,)


def test_population_rejects_only_its_immediate_structure():
    """Pre: malformed rank/member composition. Post: Population rejects that structure."""
    with pytest.raises(ValueError, match="contiguous"):
        Population({1: PopulationMember({"lr": 1.0})})
    with pytest.raises(TypeError, match="PopulationMember"):
        Population({0: {"lr": 1.0}})
