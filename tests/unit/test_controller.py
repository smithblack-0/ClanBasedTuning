import pytest

from clan_based_tuning import (
    ClanController,
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


def _controller(*, population_size=3, mode="min", seed=7, mutations=None):
    if mutations is None:
        mutations = {"lr": _mutation()}
    policy = ControllerPolicy(population_size, mutations, mode, seed)
    return ClanController(policy)


def _population(values, fitnesses):
    members = {
        rank: PopulationMember({"lr": value}, fitnesses[rank])
        for rank, value in enumerate(values)
    }
    return Population(members)


def test_initial_population_uses_defaults_and_independent_members():
    """Pre: fixed policy. Post: defaults survive at rank zero and members are distinct."""
    population = _controller().initial_population()

    assert len(population) == 3
    assert population.members[0].hyperparameters == {"lr": 1.0}
    assert len({id(member) for member in population.members.values()}) == 3
    assert population.missing_fitness_ranks() == (0, 1, 2)


def test_equal_policy_seed_and_calls_produce_equal_initial_populations():
    """Pre: redundant controllers. Post: their first trusted populations agree."""
    first = _controller(seed=13)
    second = _controller(seed=13)

    assert first.initial_population() == second.initial_population()


def test_next_generation_minimizes_and_retains_parent():
    """Pre: complete min-mode population. Post: best rank survives unchanged."""
    controller = _controller()
    population = _population([1.0, 2.0, 3.0], [4.0, 1.0, 2.0])

    parent_rank, next_population = controller.next_generation(population)

    assert parent_rank == 1
    assert next_population.members[1].hyperparameters == {"lr": 2.0}
    assert next_population.missing_fitness_ranks() == (0, 1, 2)


def test_next_generation_maximizes_and_breaks_ties_by_rank():
    """Pre: equal best max-mode fitness. Post: the lower rank is selected."""
    controller = _controller(mode="max")
    population = _population([1.0, 2.0, 3.0], [3.0, 3.0, 1.0])

    parent_rank, _ = controller.next_generation(population)

    assert parent_rank == 0


def test_next_generation_requires_complete_fitness_before_mutation():
    """Pre: one missing score. Post: transition fails without consuming RNG state."""
    controller = _controller(population_size=2)
    population = controller.initial_population()
    population.set_fitness(0, 1.0)
    state = controller.state_dict()

    with pytest.raises(RuntimeError, match="missing fitness"):
        controller.next_generation(population)

    assert controller.state_dict() == state


def test_next_generation_guards_only_the_trusted_population_boundary():
    """Pre: wrong object or fixed size. Post: the controller rejects that boundary."""
    controller = _controller(population_size=2)

    with pytest.raises(TypeError, match="Population"):
        controller.next_generation([])
    with pytest.raises(ValueError, match="exactly 2"):
        controller.next_generation(
            Population({0: PopulationMember({"lr": 1.0}, 1.0)})
        )


def test_random_state_round_trip_reproduces_transition():
    """Pre: restored RNG state. Post: equivalent policies produce the same transition."""
    first = _controller(population_size=2, seed=17)
    second = _controller(population_size=2, seed=999)
    population = _population([1.0, 2.0], [0.0, 1.0])
    second.load_state_dict(first.state_dict())

    assert first.next_generation(population) == second.next_generation(population)
