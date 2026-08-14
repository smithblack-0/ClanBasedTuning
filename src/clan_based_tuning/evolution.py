"""Framework-independent Clan Tuning evolution policy."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class _MutationRule:
    """Validated internal form of one user-supplied scalar mutation dictionary."""

    standard_deviation: float
    geometry: str
    minimum: float
    maximum: float

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> _MutationRule:
        """Validate and normalize the public dictionary form of a mutation rule."""

        expected = {"standard_deviation", "geometry", "minimum", "maximum"}
        supplied = set(config)
        missing = expected - supplied
        unknown = supplied - expected
        if missing:
            raise ValueError(f"mutation rule is missing required keys: {sorted(missing)!r}")
        if unknown:
            raise ValueError(f"mutation rule contains unknown keys: {sorted(unknown)!r}")

        standard_deviation = float(config["standard_deviation"])
        geometry = str(config["geometry"])
        minimum = float(config["minimum"])
        maximum = float(config["maximum"])

        if not math.isfinite(standard_deviation) or standard_deviation < 0:
            raise ValueError("mutation standard_deviation must be finite and non-negative")
        if geometry not in {"linear", "log"}:
            raise ValueError("mutation geometry must be 'linear' or 'log'")
        if not math.isfinite(minimum) or not math.isfinite(maximum):
            raise ValueError("mutation bounds must be finite")
        if minimum > maximum:
            raise ValueError("mutation minimum must not exceed maximum")
        if geometry == "log" and minimum <= 0:
            raise ValueError("log mutation requires a positive minimum")

        return cls(
            standard_deviation=standard_deviation,
            geometry=geometry,
            minimum=minimum,
            maximum=maximum,
        )

    def mutate(self, value: float, random_stream) -> float:
        """Return one bounded mutation of ``value``."""

        value = float(value)
        if not math.isfinite(value):
            raise ValueError("mutation source value must be finite")
        if self.geometry == "log" and value <= 0:
            raise ValueError("log mutation requires a positive source value")

        displacement = random_stream.gauss(0.0, self.standard_deviation)
        if self.geometry == "linear":
            candidate = value + displacement
        else:
            candidate = value * math.exp(displacement)
        return min(max(candidate, self.minimum), self.maximum)


def select_winner_id(population, mode):
    """Return one stable winner from rank-ordered fitness values."""

    ranked = enumerate(population)
    if mode == "min":
        return min(ranked, key=lambda item: (item[1], item[0]))[0]
    if mode == "max":
        return max(ranked, key=lambda item: (item[1], -item[0]))[0]
    raise ValueError("mode must be 'min' or 'max'")
