"""Worker-local checkpoint-source state for Clan Tuning."""

import math
from collections.abc import Callable


class ClanController:
    """Store local fitness and cache whether this worker is the checkpoint source.

    ``resolve_checkpoint_source`` is supplied by the runtime integration. It receives
    this worker's finite local fitness and returns whether this worker is the sole
    checkpoint source. The resolver owns any population synchronization, membership,
    comparison, and failure handling required to produce that answer.

    This class does not define a communication backend or inspect the population.
    """

    def __init__(
        self,
        *,
        resolve_checkpoint_source: Callable[[float], bool],
    ):
        self._resolve_checkpoint_source = resolve_checkpoint_source
        self._fitness = None
        self._checkpoint_source_decision = None

    def set_fitness(self, fitness):
        """Store this worker's finite local fitness once."""

        if self._fitness is not None:
            raise RuntimeError("fitness is already set")
        if not math.isfinite(fitness):
            raise ValueError("fitness must be finite")
        self._fitness = float(fitness)

    def should_save_checkpoint(self):
        """Resolve once whether this worker is the checkpoint source.

        The first call delegates the complete population decision to the injected
        resolver. Later calls return the cached boolean and do not invoke the resolver
        again.
        """

        if self._fitness is None:
            raise RuntimeError("fitness must be set before resolving the checkpoint source")
        if self._checkpoint_source_decision is not None:
            return self._checkpoint_source_decision

        decision = self._resolve_checkpoint_source(self._fitness)
        if not isinstance(decision, bool):
            raise TypeError("checkpoint source resolver must return bool")

        self._checkpoint_source_decision = decision
        return decision
