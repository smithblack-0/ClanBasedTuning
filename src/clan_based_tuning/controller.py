"""Framework-independent Clan population policy."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any, Literal


@dataclass(frozen=True)
class MemberResult:
    """Fitness and optimizer configuration reported by one Clan member.

    The controller reads this record only to compare fitness and obtain the
    selected parent's optimizer configuration. It never applies the configuration
    to a live optimizer or owns any training state.
    """

    fitness: float
    optimizer_config: Mapping[str, Any]


@dataclass(frozen=True)
class PopulationDecision:
    """One complete population-policy result for later framework execution.

    ``optimizer_configs`` maps every input member identity to the optimizer
    configuration values that member should receive in the next generation.
    The record contains values only; applying them to optimizers is a later
    integration responsibility.
    """

    parent_id: str
    parent_fitness: float
    optimizer_configs: Mapping[str, Mapping[str, Any]]


class ClanPopulationPolicy:
    """Select one parent and emit the next optimizer-configuration population.

    The policy is champion-centered: the best member under ``mode`` is the sole
    parent, that member retains the exact parent optimizer configuration, and
    every other member receives a copied parent configuration with explicitly
    named numeric fields scaled by one of the caller-supplied factors.

    The object is stateless. Randomness is supplied explicitly to ``decide`` by a
    seed, making repeated calls reproducible without controller persistence.
    """

    def __init__(
        self,
        *,
        mode: Literal["min", "max"],
        field_factors: Mapping[str, Sequence[float]],
    ) -> None:
        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")
        if not field_factors:
            raise ValueError("field_factors must name at least one optimizer field")

        normalized_factors: dict[str, tuple[float, ...]] = {}
        for field, factors in field_factors.items():
            if not isinstance(field, str) or not field:
                raise ValueError("optimizer field names must be non-empty strings")
            normalized = tuple(float(factor) for factor in factors)
            if not normalized:
                raise ValueError(f"field {field!r} must provide at least one scale factor")
            if any(not math.isfinite(factor) or factor <= 0.0 for factor in normalized):
                raise ValueError(f"field {field!r} scale factors must be finite and positive")
            if any(factor == 1.0 for factor in normalized):
                raise ValueError(
                    f"field {field!r} scale factors must change the value; "
                    "the selected parent already retains the exact configuration"
                )
            normalized_factors[field] = normalized

        self._mode = mode
        self._field_factors = normalized_factors

    @property
    def mode(self) -> Literal["min", "max"]:
        """Return whether lower or higher fitness wins."""

        return self._mode

    @property
    def field_factors(self) -> Mapping[str, tuple[float, ...]]:
        """Return a copy of the configured numeric exploration factors."""

        return dict(self._field_factors)

    def decide(
        self,
        population: Mapping[str, MemberResult],
        *,
        seed: int,
    ) -> PopulationDecision:
        """Return one complete, reproducible next-generation policy decision."""

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")

        validated = self._validate_population(population)
        parent_id = self._select_parent(validated)
        parent_result = validated[parent_id]
        parent_config = dict(parent_result.optimizer_config)
        self._validate_parent_fields(parent_config)

        member_ids = sorted(validated)
        challenger_ids = [member_id for member_id in member_ids if member_id != parent_id]
        assignments = self._factor_assignments(challenger_ids, seed=seed)

        optimizer_configs: dict[str, dict[str, Any]] = {}
        for member_id in member_ids:
            next_config = dict(parent_config)
            if member_id != parent_id:
                for field, factor in assignments[member_id].items():
                    next_config[field] = next_config[field] * factor
                    if not math.isfinite(float(next_config[field])):
                        raise ValueError(
                            f"scaling field {field!r} produced a non-finite value"
                        )
            optimizer_configs[member_id] = next_config

        return PopulationDecision(
            parent_id=parent_id,
            parent_fitness=float(parent_result.fitness),
            optimizer_configs=optimizer_configs,
        )

    def _factor_assignments(
        self,
        challenger_ids: Sequence[str],
        *,
        seed: int,
    ) -> dict[str, dict[str, float]]:
        generator = random.Random(seed)
        assignments = {member_id: {} for member_id in challenger_ids}
        for field, factors in self._field_factors.items():
            ordered_factors = list(factors)
            generator.shuffle(ordered_factors)
            for index, member_id in enumerate(challenger_ids):
                assignments[member_id][field] = ordered_factors[index % len(ordered_factors)]
        return assignments

    def _select_parent(self, population: Mapping[str, MemberResult]) -> str:
        if self._mode == "min":
            return min(population, key=lambda member_id: (population[member_id].fitness, member_id))
        return min(population, key=lambda member_id: (-population[member_id].fitness, member_id))

    def _validate_population(
        self,
        population: Mapping[str, MemberResult],
    ) -> dict[str, MemberResult]:
        if not isinstance(population, Mapping):
            raise TypeError("population must be a mapping from member IDs to MemberResult")
        if len(population) < 2:
            raise ValueError("a Clan population must contain at least two members")

        validated: dict[str, MemberResult] = {}
        for member_id, result in population.items():
            if not isinstance(member_id, str) or not member_id:
                raise ValueError("member IDs must be non-empty strings")
            if not isinstance(result, MemberResult):
                raise TypeError("every population value must be a MemberResult")
            if isinstance(result.fitness, bool) or not isinstance(result.fitness, Real):
                raise TypeError(f"fitness for member {member_id!r} must be a real scalar")
            if not math.isfinite(float(result.fitness)):
                raise ValueError(f"fitness for member {member_id!r} must be finite")
            if not isinstance(result.optimizer_config, Mapping):
                raise TypeError(
                    f"optimizer_config for member {member_id!r} must be a mapping"
                )
            validated[member_id] = MemberResult(
                fitness=float(result.fitness),
                optimizer_config=dict(result.optimizer_config),
            )
        return validated

    def _validate_parent_fields(self, parent_config: Mapping[str, Any]) -> None:
        for field in self._field_factors:
            if field not in parent_config:
                raise ValueError(f"selected parent optimizer config is missing field {field!r}")
            value = parent_config[field]
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(
                    f"selected parent optimizer field {field!r} must be a real scalar"
                )
            if not math.isfinite(float(value)):
                raise ValueError(
                    f"selected parent optimizer field {field!r} must be finite"
                )
