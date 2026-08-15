"""Framework-independent Clan generation policy.

This module owns the calculations that turn one completed Clan generation into the next.
Framework adapters supply member-ordered fitness/config state; this module selects one parent,
snapshots it once, and derives every child config from that same snapshot. Keeping this logic
free of Ray and Lightning is what makes seeded sibling generation reproducible independently
of framework scheduling order.
"""

import copy
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class _GaussianRandom(Protocol):
    """Minimum random interface needed by mutation policy.

    The scheduler owns the concrete random stream so its state is serialized with Tune. Tests
    can provide a deterministic stand-in without coupling the policy to ``random.Random``.
    """

    def gauss(self, mean: float, standard_deviation: float) -> float:
        """Provide the Gaussian displacement consumed by one mutation."""


@dataclass(frozen=True, slots=True)
class _MutationRule:
    """Validated scalar mutation policy kept deliberately ignorant of parameter meaning.

    ``linear`` applies additive Gaussian displacement. ``log`` applies Gaussian displacement
    in log space, preserving multiplicative scale. Bounds are applied after mutation so every
    generated child remains inside the user's declared search region.
    """

    standard_deviation: float
    geometry: str
    minimum: float
    maximum: float

    def mutate(self, value: float, random_stream: _GaussianRandom) -> float:
        """Apply this rule without interpreting what the controlled genome value does.

        Log geometry requires a positive source because mutation is multiplicative. The rule
        clips only the proposed child value; it never changes the stored parent snapshot.
        """

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
    """Complete framework-independent decision for one Clan boundary.

    ``parent_config`` is a deep snapshot taken before any child mutation. ``child_configs`` is
    indexed by stable Clan member ID, and every entry—including the prior winner—is an
    independent mutation of that same parent snapshot. Framework adapters may transfer this
    decision but must not reinterpret or regenerate it.
    """

    winner_id: int
    parent_config: dict[str, Any]
    child_configs: tuple[dict[str, Any], ...]


# Construction


def build_mutation_rule(
    config: Mapping[str, Any],
    _cls: type[_MutationRule] = _MutationRule,
) -> _MutationRule:
    """Normalize one user mutation declaration before generation-time execution.

    Validation happens once when the scheduler is constructed so generation transitions do
    not repeatedly rediscover malformed search-space metadata. This function validates only
    mutation geometry and numeric bounds; the genome key's optimizer/model meaning remains
    userspace-owned.

    Args:
        config: Mapping containing exactly ``standard_deviation``, ``geometry``, ``minimum``,
            and ``maximum``.
        _cls: Replacement normalized rule type that must preserve the same mutation contract.

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


# Main


def select_winner_id(population: Sequence[float], mode: str) -> int:
    """Select one parent deterministically from member-ordered fitness values.

    Stable member order is part of the algorithm, not presentation: exact ties resolve to the
    lower member ID so worker-side and driver-side selection cannot depend on incidental
    container ordering. Non-finite values are rejected because NaN/inf ordering would make
    that agreement unreliable.
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
    """Freeze one parent and construct the entire next generation in stable member order.

    The parent config is deep-copied before the first mutation. Each child then starts from a
    fresh deep copy of that snapshot, which prevents sibling mutations from accumulating on
    each other. Iterating children by stable member ID makes a serialized RNG state produce
    the same sibling assignment regardless of Ray trial iteration order.

    ``mutations`` may touch only declared user config keys; this function deliberately knows
    nothing about how user code later applies those values to an optimizer or model.

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
