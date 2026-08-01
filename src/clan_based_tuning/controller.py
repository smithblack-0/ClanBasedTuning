"""Worker-side collective checkpoint decision for Clan Tuning."""

import math
from collections.abc import Mapping
from typing import Protocol

from clan_based_tuning.evolution import select_winner_id


class PopulationRuntime(Protocol):
    """Return complete member-associated fitness for one population boundary."""

    def resolve(self, local_fitness: float) -> Mapping[int, float]: ...


class ClanController:
    """Resolve whether this Tune worker should provide the round checkpoint.

    The controller is deliberately ephemeral. It owns one local fitness value and one
    population decision. Population transport, evolution, trial configuration,
    checkpoint loading, and scheduler state belong to their surrounding owners.
    """

    def __init__(
        self,
        *,
        member_id: int,
        population_size: int,
        mode: str,
        population_runtime: PopulationRuntime,
    ):
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        if not 0 <= member_id < population_size:
            raise ValueError("member_id must identify one member of the population")
        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")

        self.member_id = member_id
        self.population_size = population_size
        self._mode = mode
        self._population_runtime = population_runtime
        self._fitness = None
        self._save_checkpoint = None

    def set_fitness(self, fitness):
        """Store this worker's finite fitness for the population decision."""

        if self._fitness is not None:
            raise RuntimeError("fitness is already set")
        if not math.isfinite(fitness):
            raise ValueError("fitness must be finite")
        self._fitness = float(fitness)

    def should_save_checkpoint(self):
        """Resolve fitness once and return whether this worker is the winner.

        The first call blocks in the configured population runtime. Later calls return
        the cached decision and never enter population communication again.
        """

        if self._fitness is None:
            raise RuntimeError("fitness must be set before resolving the checkpoint")
        if self._save_checkpoint is not None:
            return self._save_checkpoint

        population = dict(self._population_runtime.resolve(self._fitness))
        expected_members = set(range(self.population_size))
        if set(population) != expected_members:
            raise RuntimeError("population runtime returned the wrong member set")
        if any(not math.isfinite(fitness) for fitness in population.values()):
            raise RuntimeError("population runtime returned a non-finite value")

        ordered_fitness = [population[member_id] for member_id in range(self.population_size)]
        winner_id = select_winner_id(ordered_fitness, self._mode)
        self._save_checkpoint = self.member_id == winner_id
        return self._save_checkpoint
