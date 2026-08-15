"""Framework-independent Clan generation policy.

This module owns the calculations that turn one completed Clan generation into the next.
It validates mutation rules, selects the single parent, and deterministically constructs one
independently mutated child config per stable member. Framework adapters supply fitnesses and
configs in member order and apply the returned decision; this module does not know about Ray,
Lightning, checkpoints, or optimizer semantics.
"""

import copy
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class _GaussianRandom(Protocol):
    """Random source required by scalar Clan mutation."""

    def gauss(self, mean: float, standard_deviation: float) -> float:
        """Return one Gaussian sample."""


@dataclass(frozen=True, slots=True)
class _MutationRule:
    """Normalized internal form of one scalar mutation rule."""

    standard_deviation: float
    geometry: str
    minimum: float
    maximum: float

    def mutate(self, value: float, random_stream: _GaussianRandom) -> float:
        """Return one bounded mutation of ``value`` using ``random_stream``."""

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


@dataclass(frozen=True, slots=True)
class GenerationDecision:
    """Resolved parent and complete next-generation configs for one Clan boundary.

    ``child_configs`` is indexed by stable Clan member ID. Every child, including the prior
    winner, is independently mutated from the same snapshotted parent config.
    """

    winner_id: int
    parent_config: dict[str, Any]
    child_configs: tuple[dict[str, Any], ...]


# Helpers


def build_mutation_rule(
    config: Mapping[str, Any],
    _cls: type[_MutationRule] = _MutationRule,
) -> _MutationRule:
    """Validate one public mutation dictionary and return its normalized rule.

    Args:
        config: Mapping containing exactly ``standard_deviation``, ``geometry``, ``minimum``,
            and ``maximum``.
        _cls: Injectable normalized rule type for isolated construction tests.

    Returns:
        Validated immutable mutation rule.

    Raises:
        ValueError: If required fields, geometry, bounds, or numeric values are invalid.
    """

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

    return _cls(
        standard_deviation=standard_deviation,
        geometry=geometry,
        minimum=minimum,
        maximum=maximum,
    )


def build_mutation_rules(
    configs: Mapping[str, Mapping[str, Any]],
    _build_rule: Callable[[Mapping[str, Any]], _MutationRule] = build_mutation_rule,
) -> dict[str, _MutationRule]:
    """Normalize all mutation dictionaries while preserving user genome keys.

    Args:
        configs: Mutation dictionaries keyed by the corresponding Tune config/genome field.
        _build_rule: Injectable single-rule construction function for isolated tests.

    Returns:
        Validated immutable mutation rules keyed by the original user genome fields.
    """

    return {key: _build_rule(config) for key, config in configs.items()}


# Main


def select_winner_id(population: Sequence[float], mode: str) -> int:
    """Return the stable winning member ID from finite member-ordered fitness values.

    Ties are resolved by lower stable member ID for both minimization and maximization.

    Raises:
        ValueError: If the population is empty, contains non-finite fitness, or uses an
            unsupported comparison mode.
    """

    fitnesses = [float(value) for value in population]
    if not fitnesses:
        raise ValueError("population must contain at least one fitness")
    if any(not math.isfinite(value) for value in fitnesses):
        raise ValueError("population fitnesses must be finite")

    ranked = enumerate(fitnesses)
    if mode == "min":
        return min(ranked, key=lambda item: (item[1], item[0]))[0]
    if mode == "max":
        return max(ranked, key=lambda item: (item[1], -item[0]))[0]
    raise ValueError("mode must be 'min' or 'max'")


def resolve_generation(
    fitnesses: Sequence[float],
    configs: Sequence[Mapping[str, Any]],
    mode: str,
    mutations: Mapping[str, _MutationRule],
    random_stream: _GaussianRandom,
    _select_winner: Callable[[Sequence[float], str], int] = select_winner_id,
) -> GenerationDecision:
    """Resolve one complete Clan boundary into a parent and next-generation configs.

    Args:
        fitnesses: Finite candidate fitnesses in stable member-ID order.
        configs: Current Tune configs in the same stable member-ID order.
        mode: ``"min"`` or ``"max"`` selection direction.
        mutations: Normalized mutation rules keyed by user genome/config field.
        random_stream: Scheduler-owned random stream whose state persists with the scheduler.
        _select_winner: Injectable winner-selection function for isolated composition tests.

    Returns:
        One winner plus a complete tuple of independently mutated child configs.

    Raises:
        ValueError: If population inputs are empty, misaligned, or contain non-finite fitness.
        KeyError: If the selected parent config lacks a configured mutation key.
    """

    if not fitnesses:
        raise ValueError("generation must contain at least one member")
    if len(fitnesses) != len(configs):
        raise ValueError("fitness and config populations must have equal length")
    if any(not math.isfinite(float(fitness)) for fitness in fitnesses):
        raise ValueError("generation fitnesses must be finite")

    winner_id = _select_winner([float(value) for value in fitnesses], mode)
    parent_config = copy.deepcopy(dict(configs[winner_id]))

    child_configs = []
    for _member_id in range(len(configs)):
        child = copy.deepcopy(parent_config)
        for key, mutation in mutations.items():
            if key not in child:
                raise KeyError(f"Clan mutation key {key!r} is missing from the Tune config")
            child[key] = mutation.mutate(child[key], random_stream)
        child_configs.append(child)

    return GenerationDecision(
        winner_id=winner_id,
        parent_config=parent_config,
        child_configs=tuple(child_configs),
    )
