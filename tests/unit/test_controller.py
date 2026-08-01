import math

import pytest

from clan_based_tuning import ClanController


class CheckpointSourceResolver:
    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def __call__(self, local_fitness):
        self.calls.append(local_fitness)
        return self.decision


def _controller(decision):
    resolver = CheckpointSourceResolver(decision)
    controller = ClanController(resolve_checkpoint_source=resolver)
    return controller, resolver


@pytest.mark.parametrize("decision", [True, False])
def test_checkpoint_source_decision_is_cached(decision):
    controller, resolver = _controller(decision)
    controller.set_fitness(1.25)

    assert controller.should_save_checkpoint() is decision
    assert controller.should_save_checkpoint() is decision
    assert resolver.calls == [1.25]


def test_fitness_must_be_set_before_checkpoint_source_resolution():
    controller, resolver = _controller(True)

    with pytest.raises(RuntimeError, match="fitness"):
        controller.should_save_checkpoint()

    assert resolver.calls == []


@pytest.mark.parametrize("fitness", [math.nan, math.inf, -math.inf])
def test_nonfinite_fitness_is_rejected_before_resolution(fitness):
    controller, resolver = _controller(True)

    with pytest.raises(ValueError, match="finite"):
        controller.set_fitness(fitness)

    assert resolver.calls == []


def test_fitness_cannot_change_after_assignment():
    controller, resolver = _controller(True)
    controller.set_fitness(1.0)

    with pytest.raises(RuntimeError, match="already"):
        controller.set_fitness(0.5)

    assert resolver.calls == []


def test_checkpoint_source_resolver_must_return_bool():
    controller = ClanController(resolve_checkpoint_source=lambda local_fitness: 1)
    controller.set_fitness(1.0)

    with pytest.raises(TypeError, match="return bool"):
        controller.should_save_checkpoint()


def test_controller_has_no_population_evolution_or_serialization_api():
    controller, _ = _controller(True)

    assert not hasattr(controller, "population_size")
    assert not hasattr(controller, "mode")
    assert not hasattr(controller, "advance")
    assert not hasattr(controller, "get_config")
    assert not hasattr(controller, "genome")
    assert not hasattr(controller, "get_genome")
    assert not hasattr(controller, "state_dict")
    assert not hasattr(controller, "load_state_dict")
