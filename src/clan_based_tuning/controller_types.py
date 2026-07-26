"""Small data objects used by the framework-independent Clan controller.

The controller evolves named scalar values. Distributed storage and state transfer
remain external effects supplied through callbacks.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MutationSpec:
    """Apply one local mutation rule to a named scalar value."""

    standard_deviation: float
    geometry: str
    minimum: float
    maximum: float

    def mutate(self, value, random_stream):
        """Return one bounded mutation of ``value``."""

        displacement = random_stream.gauss(0.0, self.standard_deviation)
        if self.geometry == "linear":
            candidate = value + displacement
        elif self.geometry == "log":
            candidate = value * math.exp(displacement)
        else:
            raise ValueError(f"unknown mutation geometry: {self.geometry}")
        return min(max(candidate, self.minimum), self.maximum)


@dataclass(slots=True)
class ClanRound:
    """Carry one member's configuration into a round and publish its result.

    The callback decides how a completed round is stored or communicated. The round
    only knows that assigning fitness publishes this member's completed local state.
    """

    member_id: int
    round_index: int
    config: dict[str, float]
    save_member_fitness: Callable[["ClanRound"], None] = field(repr=False, compare=False)
    fitness: float | None = None

    def __post_init__(self):
        self.config = dict(self.config)

    def get_config(self):
        """Return a copy of the controlled values used for this round."""

        return dict(self.config)

    def set_fitness(self, fitness):
        """Attach this round's comparable result and publish the completed round."""

        if not math.isfinite(fitness):
            raise ValueError("fitness must be finite")
        self.fitness = float(fitness)
        self.save_member_fitness(self)
