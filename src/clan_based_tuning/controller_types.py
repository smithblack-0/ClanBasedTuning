"""Framework-independent mutation rules used by the CBT scheduler."""

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
