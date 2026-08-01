"""Ray collective runtime for Clan population boundaries."""

from collections.abc import Sequence
from queue import Queue
from threading import Thread


class RayPopulationRuntime:
    """All-gather fitness for one stable Clan through a persistent Ray GLOO group.

    Collective rank is transport state, not member identity. The runtime records the
    explicit mapping and returns fitness keyed by stable member ID. The surrounding
    worker integration initializes the complete group before any population boundary and
    destroys it when the live Clan ends.
    """

    def __init__(
        self,
        *,
        member_id: int,
        member_ids_by_rank: Sequence[int],
        group_name: str,
        timeout_ms: int,
    ):
        member_ids_by_rank = tuple(member_ids_by_rank)
        population_size = len(member_ids_by_rank)
        if population_size < 2:
            raise ValueError("member_ids_by_rank must contain at least two members")
        if set(member_ids_by_rank) != set(range(population_size)):
            raise ValueError("member_ids_by_rank must contain every stable member exactly once")
        if member_id not in member_ids_by_rank:
            raise ValueError("member_id must identify one configured stable member")
        if not group_name:
            raise ValueError("group_name must be non-empty")
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")

        self.member_id = member_id
        self.member_ids_by_rank = member_ids_by_rank
        self.group_name = group_name
        self.timeout_ms = timeout_ms
        self._rank = member_ids_by_rank.index(member_id)

    def initialize(self) -> None:
        """Join the complete Ray collective group before population resolution."""

        import ray.util.collective as collective

        collective.init_collective_group(
            world_size=len(self.member_ids_by_rank),
            rank=self._rank,
            backend="gloo",
            group_name=self.group_name,
            gloo_timeout=self.timeout_ms,
        )

    def resolve(self, local_fitness: float) -> dict[int, float]:
        """Return complete fitness keyed by stable member identity.

        CPU ``float64`` transport preserves the comparison semantics of Python fitness
        values more closely than ``float32`` while keeping the population collective
        independent of the model-training device.

        Ray 2.56 applies its GLOO timeout to rendezvous but not to the underlying torch
        collective operation. The all-gather therefore runs on a daemon thread. If it
        cannot complete within the configured boundary, the current Ray actor exits so
        the invalid Clan fails visibly instead of leaving a worker blocked indefinitely.
        """

        import ray
        import ray.util.collective as collective
        import torch

        if not collective.is_group_initialized(self.group_name):
            raise RuntimeError("population collective group is not initialized")

        outcome = Queue(maxsize=1)

        def allgather():
            try:
                local = torch.tensor([local_fitness], dtype=torch.float64, device="cpu")
                gathered = [torch.empty_like(local) for _ in self.member_ids_by_rank]
                collective.allgather(gathered, local, self.group_name)
                population = {
                    member_id: float(fitness.item())
                    for member_id, fitness in zip(self.member_ids_by_rank, gathered, strict=True)
                }
                outcome.put((population, None))
            except Exception as error:
                outcome.put((None, error))

        operation = Thread(target=allgather, daemon=True)
        operation.start()
        operation.join(self.timeout_ms / 1000)

        if operation.is_alive():
            ray.actor.exit_actor()
            raise RuntimeError("population collective timed out")

        population, error = outcome.get_nowait()
        if error is not None:
            raise error
        if population is None:
            raise RuntimeError("population collective returned no result")
        return population

    def destroy(self) -> None:
        """Release this worker's collective resources when the live Clan ends."""

        import ray.util.collective as collective

        if collective.is_group_initialized(self.group_name):
            collective.destroy_collective_group(self.group_name)
