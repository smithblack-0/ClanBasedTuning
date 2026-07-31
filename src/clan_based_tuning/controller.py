"""Worker-side collective checkpoint decision for Clan Tuning."""

import math
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType

from clan_based_tuning.evolution import select_winner_id
from clan_based_tuning.scheduler_types import Genome


class ClanController:
    """Resolve and record this worker's checkpoint-source decision.

    The controller is ephemeral. It owns one immutable copy of the scheduler-assigned
    genome, one local fitness value, and one cached collective decision. It does not
    mutate genomes, advance generations, or own scheduler persistence.
    """

    def __init__(
        self,
        *,
        member_id: int,
        population_size: int,
        mode: str,
        genome: Genome,
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
        self._genome: Mapping[str, object] = MappingProxyType(dict(genome))
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

        winner_id = select_winner_id(population, self._mode)
        self._save_checkpoint = self.member_id == winner_id
        return self._save_checkpoint

    def save_genome(self, checkpoint):
        """Attach this selected worker's genome provenance to ``checkpoint``.

        The method reads the cached save decision and never re-enters the fitness
        collective. The scheduler remains authoritative over genomes and future
        assignments; this metadata only records which assignment produced the payload.
        """

        if self._save_checkpoint is None:
            raise RuntimeError("checkpoint source must be resolved before saving the genome")
        if not self._save_checkpoint:
            raise RuntimeError("only the selected checkpoint source may save its genome")

        checkpoint.update_metadata(
            {
                "clan_based_tuning": {
                    "schema_version": 1,
                    "member_id": self.member_id,
                    "genome": dict(self._genome),
                }
            }
        )
        return checkpoint
