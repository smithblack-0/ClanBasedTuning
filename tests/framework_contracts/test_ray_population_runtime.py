"""Ray contracts for complete member-associated population resolution."""

import math
import uuid

import pytest

from clan_based_tuning import ClanController
from clan_based_tuning.ray_population import RayPopulationRuntime

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
ray = pytest.importorskip("ray")


@ray.remote
class PopulationMember:
    def __init__(self, member_id, member_ids_by_rank):
        self.member_id = member_id
        self.member_ids_by_rank = tuple(member_ids_by_rank)

    def resolve(self, fitness, group_name, gloo_timeout_ms=30_000):
        runtime = RayPopulationRuntime(
            member_id=self.member_id,
            member_ids_by_rank=self.member_ids_by_rank,
            group_name=group_name,
            gloo_timeout_ms=gloo_timeout_ms,
        )
        return runtime.resolve(fitness)

    def should_save(self, fitness, group_name, mode):
        runtime = RayPopulationRuntime(
            member_id=self.member_id,
            member_ids_by_rank=self.member_ids_by_rank,
            group_name=group_name,
        )
        controller = ClanController(
            member_id=self.member_id,
            population_size=len(self.member_ids_by_rank),
            mode=mode,
            population_runtime=runtime,
        )
        controller.set_fitness(fitness)
        first = controller.should_save_checkpoint()
        second = controller.should_save_checkpoint()
        return first, second


@pytest.fixture
def local_ray():
    ray.shutdown()
    ray.init(num_cpus=3, include_dashboard=False, log_to_driver=False)
    try:
        yield
    finally:
        ray.shutdown()


def _group_name():
    return f"cbt-{uuid.uuid4().hex}"


def _members(member_ids_by_rank):
    return {
        member_id: PopulationMember.remote(member_id, member_ids_by_rank)
        for member_id in member_ids_by_rank
    }


def test_allgather_preserves_stable_member_identity_and_float64_precision(local_ray):
    member_ids_by_rank = (2, 0, 1)
    members = _members(member_ids_by_rank)
    population = {
        0: math.nextafter(1.0, math.inf),
        1: 1.0,
        2: 3.0,
    }
    group_name = _group_name()

    results = ray.get(
        [
            members[member_id].resolve.remote(population[member_id], group_name)
            for member_id in population
        ]
    )

    assert results == [population, population, population]


def test_controller_resolves_once_across_consecutive_generations(local_ray):
    member_ids_by_rank = (2, 0, 1)
    members = _members(member_ids_by_rank)

    first_population = {0: 4.0, 1: 1.0, 2: 2.0}
    first_group = _group_name()
    first_results = ray.get(
        [
            members[member_id].should_save.remote(
                first_population[member_id], first_group, "min"
            )
            for member_id in range(3)
        ]
    )
    assert first_results == [(False, False), (True, True), (False, False)]

    second_population = {0: 5.0, 1: 5.0, 2: 2.0}
    second_group = _group_name()
    second_results = ray.get(
        [
            members[member_id].should_save.remote(
                second_population[member_id], second_group, "max"
            )
            for member_id in range(3)
        ]
    )
    assert second_results == [(True, True), (False, False), (False, False)]


def test_missing_member_surfaces_collective_failure(local_ray):
    member_ids_by_rank = (0, 1)
    member = PopulationMember.remote(0, member_ids_by_rank)

    result = member.resolve.remote(1.0, _group_name(), 1_000)

    with pytest.raises(ray.exceptions.RayTaskError):
        ray.get(result, timeout=15)
