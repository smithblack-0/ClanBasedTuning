"""Framework-independent Clan Tuning evolution policy."""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MutationSpec:
    """Apply one bounded mutation rule to a named scalar value."""

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


def select_winner_id(population, mode):
    """Return one stable winner from rank-ordered fitness values."""

    ranked = enumerate(population)
    if mode == "min":
        return min(ranked, key=lambda item: (item[1], item[0]))[0]
    if mode == "max":
        return max(ranked, key=lambda item: (item[1], -item[0]))[0]
    raise ValueError("mode must be 'min' or 'max'")
