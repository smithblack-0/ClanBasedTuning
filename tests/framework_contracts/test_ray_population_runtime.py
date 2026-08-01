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
    def __init__(self, member_id, member_ids_by_rank, group_name, timeout_ms):
        self.member_id = member_id
        self.member_ids_by_rank = tuple(member_ids_by_rank)
        self.runtime = RayPopulationRuntime(
            member_id=member_id,
            member_ids_by_rank=member_ids_by_rank,
            group_name=group_name,
            timeout_ms=timeout_ms,
        )

    def initialize(self):
        self.runtime.initialize()

    def resolve(self, fitness):
        return self.runtime.resolve(fitness)

    def should_save(self, fitness, mode):
        controller = ClanController(
            member_id=self.member_id,
            population_size=len(self.member_ids_by_rank),
            mode=mode,
            population_runtime=self.runtime,
        )
        controller.set_fitness(fitness)
        first = controller.should_save_checkpoint()
        second = controller.should_save_checkpoint()
        return first, second

    def destroy(self):
        self.runtime.destroy()


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


def _members(member_ids_by_rank, *, timeout_ms=30_000):
    group_name = _group_name()
    members = {
        member_id: PopulationMember.remote(
            member_id,
            member_ids_by_rank,
            group_name,
            timeout_ms,
        )
        for member_id in member_ids_by_rank
    }
    ray.get([member.initialize.remote() for member in members.values()])
    return members


def _destroy(members):
    ray.get([member.destroy.remote() for member in members.values()])


def test_allgather_preserves_stable_member_identity_and_float64_precision(local_ray):
    member_ids_by_rank = (2, 0, 1)
    members = _members(member_ids_by_rank)
    population = {
        0: math.nextafter(1.0, math.inf),
        1: 1.0,
        2: 3.0,
    }

    try:
        results = ray.get(
            [members[member_id].resolve.remote(population[member_id]) for member_id in population]
        )
    finally:
        _destroy(members)

    assert results == [population, population, population]


def test_controller_resolves_once_across_consecutive_generations(local_ray):
    member_ids_by_rank = (2, 0, 1)
    members = _members(member_ids_by_rank)

    try:
        first_population = {0: 4.0, 1: 1.0, 2: 2.0}
        first_results = ray.get(
            [
                members[member_id].should_save.remote(first_population[member_id], "min")
                for member_id in range(3)
            ]
        )
        assert first_results == [(False, False), (True, True), (False, False)]

        second_population = {0: 5.0, 1: 5.0, 2: 2.0}
        second_results = ray.get(
            [
                members[member_id].should_save.remote(second_population[member_id], "max")
                for member_id in range(3)
            ]
        )
        assert second_results == [(True, True), (False, False), (False, False)]
    finally:
        _destroy(members)


def test_missing_member_exits_the_blocked_actor(local_ray):
    members = _members((0, 1), timeout_ms=1_000)

    result = members[0].resolve.remote(1.0)

    with pytest.raises(ray.exceptions.RayActorError):
        ray.get(result, timeout=15)
