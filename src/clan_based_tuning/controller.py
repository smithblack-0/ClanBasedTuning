"""Worker-side collective checkpoint decision for Clan Tuning."""

import math
from collections.abc import Callable, Sequence


class ClanController:
    """Resolve whether this Tune worker should provide the round checkpoint.

    The controller is deliberately ephemeral. It owns one local fitness value and one
    collective decision. Population evolution, trial configuration, checkpoint loading,
    and scheduler state belong to the Tune scheduler and surrounding training function.
    """

    def __init__(
        self,
        *,
        member_id: int,
        population_size: int,
        mode: str,
        exchange_fitness: Callable[[float], Sequence[float]],
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
        self._exchange_fitness = exchange_fitness
        self._fitness = None
        self._save_checkpoint = None

    def set_fitness(self, fitness):
        """Store this worker's finite fitness for the collective decision."""

        if self._fitness is not None:
            raise RuntimeError("fitness is already set")
        if not math.isfinite(fitness):
            raise ValueError("fitness must be finite")
        self._fitness = float(fitness)

    def should_save_checkpoint(self):
        """Collect fitness once and return whether this worker is the winner.

        The first call blocks in the injected collective exchange. Later calls return
        the cached decision and never enter the collective again.
        """

        if self._fitness is None:
            raise RuntimeError("fitness must be set before resolving the checkpoint")
        if self._save_checkpoint is not None:
            return self._save_checkpoint

        population = list(self._exchange_fitness(self._fitness))
        if len(population) != self.population_size:
            raise RuntimeError("fitness collective returned the wrong population size")
        if any(not math.isfinite(fitness) for fitness in population):
            raise RuntimeError("fitness collective returned a non-finite value")

        winner_id = self._select_winner(population)
        self._save_checkpoint = self.member_id == winner_id
        return self._save_checkpoint

    def _select_winner(self, population):
        ranked = enumerate(population)
        if self._mode == "min":
            return min(ranked, key=lambda item: (item[1], item[0]))[0]
        return max(ranked, key=lambda item: (item[1], -item[0]))[0]
