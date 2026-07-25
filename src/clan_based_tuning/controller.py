"""Framework-independent Clan population controller."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any, Literal

_REQUIRED_SPEC_KEYS = frozenset({"default", "std", "sampling", "lower", "upper"})
_REQUIRED_RESULT_KEYS = frozenset({"fitness", "config"})


class ClanController:
    """Transform completed Clan populations into optimizer configurations.

    The controller owns only evolutionary policy. It initializes one complete
    optimizer-configuration population around required defaults, selects the sole
    parent from one completed population, and emits the next complete population.
    Explicit seeds provide reproducibility without hidden mutable state.

    Parameter specifications use ordinary mappings with five required fields:
    ``default``, ``std``, ``sampling`` (``"linear"`` or ``"log"``), ``lower``,
    and ``upper``. Linear parameters receive additive normal perturbations. Log
    parameters receive normal perturbations in log coordinates, which are
    multiplicative in the original coordinates. Results are constrained to the
    declared bounds.
    """

    def __init__(
        self,
        *,
        population_size: int,
        parameters: Mapping[str, Mapping[str, Any]],
        mode: Literal["min", "max"],
    ) -> None:
        if isinstance(population_size, bool) or not isinstance(population_size, int):
            raise TypeError("population_size must be an integer")
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")

        self._population_size = population_size
        self._mode = mode
        self._parameters = self._validate_parameters(parameters)

    def initialize(
        self,
        member_ids: Sequence[str],
        *,
        seed: int,
    ) -> dict[str, dict[str, float]]:
        """Create the initial optimizer configurations around required defaults.

        The lexicographically first member retains the exact defaults as the
        control. Every other member receives an independently perturbed copy.
        """

        members = self._validate_member_ids(member_ids)
        generator = self._generator(seed)
        defaults = {
            name: float(spec["default"]) for name, spec in self._parameters.items()
        }

        configurations = {members[0]: dict(defaults)}
        for member_id in members[1:]:
            configurations[member_id] = self._mutate(defaults, generator)
        return configurations

    def advance(
        self,
        population: Mapping[str, Mapping[str, Any]],
        *,
        seed: int,
    ) -> tuple[str, dict[str, dict[str, float]]]:
        """Select the sole parent and emit the complete next population."""

        validated = self._validate_population(population)
        parent_id = self._select_parent(validated)
        parent_config = validated[parent_id]["config"]
        generator = self._generator(seed)

        configurations: dict[str, dict[str, float]] = {}
        for member_id in sorted(validated):
            if member_id == parent_id:
                configurations[member_id] = dict(parent_config)
            else:
                configurations[member_id] = self._mutate(parent_config, generator)
        return parent_id, configurations

    def _mutate(
        self,
        base_config: Mapping[str, float],
        generator: random.Random,
    ) -> dict[str, float]:
        mutated: dict[str, float] = {}
        for name, spec in self._parameters.items():
            value = float(base_config[name])
            displacement = generator.gauss(0.0, float(spec["std"]))
            lower = float(spec["lower"])
            upper = float(spec["upper"])

            if spec["sampling"] == "linear":
                candidate = value + displacement
                mutated[name] = min(max(candidate, lower), upper)
            else:
                log_candidate = math.log(value) + displacement
                log_candidate = min(
                    max(log_candidate, math.log(lower)),
                    math.log(upper),
                )
                mutated[name] = math.exp(log_candidate)
        return mutated

    def _select_parent(
        self,
        population: Mapping[str, Mapping[str, Any]],
    ) -> str:
        if self._mode == "min":
            return min(
                population,
                key=lambda member_id: (population[member_id]["fitness"], member_id),
            )
        return min(
            population,
            key=lambda member_id: (-population[member_id]["fitness"], member_id),
        )

    def _validate_population(
        self,
        population: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        if not isinstance(population, Mapping):
            raise TypeError("population must be a mapping from member IDs to results")
        if len(population) != self._population_size:
            raise ValueError(
                f"population must contain exactly {self._population_size} members"
            )

        validated: dict[str, dict[str, Any]] = {}
        expected_fields = set(self._parameters)
        for member_id, result in population.items():
            self._validate_member_id(member_id)
            if not isinstance(result, Mapping):
                raise TypeError(f"result for member {member_id!r} must be a mapping")
            if set(result) != _REQUIRED_RESULT_KEYS:
                raise ValueError(
                    f"result for member {member_id!r} must contain exactly "
                    "'fitness' and 'config'"
                )

            fitness = self._finite_real(
                result["fitness"], f"fitness for member {member_id!r}"
            )
            config = result["config"]
            if not isinstance(config, Mapping):
                raise TypeError(f"config for member {member_id!r} must be a mapping")
            if set(config) != expected_fields:
                raise ValueError(
                    f"config for member {member_id!r} must contain exactly the "
                    "configured optimizer fields"
                )

            normalized_config: dict[str, float] = {}
            for name, spec in self._parameters.items():
                value = self._finite_real(
                    config[name], f"optimizer field {name!r} for member {member_id!r}"
                )
                lower = float(spec["lower"])
                upper = float(spec["upper"])
                if not lower <= value <= upper:
                    raise ValueError(
                        f"optimizer field {name!r} for member {member_id!r} "
                        f"must be within [{lower}, {upper}]"
                    )
                normalized_config[name] = value

            validated[member_id] = {
                "fitness": fitness,
                "config": normalized_config,
            }
        return validated

    @classmethod
    def _validate_parameters(
        cls,
        parameters: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, float | str]]:
        if not isinstance(parameters, Mapping):
            raise TypeError("parameters must be a mapping")
        if not parameters:
            raise ValueError("parameters must define at least one optimizer field")

        normalized: dict[str, dict[str, float | str]] = {}
        for name in sorted(parameters):
            cls._validate_member_id(name, label="parameter names")
            spec = parameters[name]
            if not isinstance(spec, Mapping):
                raise TypeError(f"parameter specification for {name!r} must be a mapping")
            if set(spec) != _REQUIRED_SPEC_KEYS:
                raise ValueError(
                    f"parameter {name!r} must define exactly default, std, sampling, "
                    "lower, and upper"
                )

            default = cls._finite_real(spec["default"], f"default for {name!r}")
            std = cls._finite_real(spec["std"], f"std for {name!r}")
            lower = cls._finite_real(spec["lower"], f"lower bound for {name!r}")
            upper = cls._finite_real(spec["upper"], f"upper bound for {name!r}")
            sampling = spec["sampling"]

            if std <= 0.0:
                raise ValueError(f"std for {name!r} must be positive")
            if sampling not in {"linear", "log"}:
                raise ValueError(f"sampling for {name!r} must be 'linear' or 'log'")
            if lower >= upper:
                raise ValueError(f"lower bound for {name!r} must be less than upper")
            if not lower <= default <= upper:
                raise ValueError(f"default for {name!r} must be within its bounds")
            if sampling == "log" and lower <= 0.0:
                raise ValueError(f"log parameter {name!r} requires a positive lower bound")

            normalized[name] = {
                "default": default,
                "std": std,
                "sampling": sampling,
                "lower": lower,
                "upper": upper,
            }
        return normalized

    @staticmethod
    def _finite_real(value: Any, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{label} must be a real scalar")
        normalized = float(value)
        if not math.isfinite(normalized):
            raise ValueError(f"{label} must be finite")
        return normalized

    def _validate_member_ids(self, member_ids: Sequence[str]) -> list[str]:
        if isinstance(member_ids, str | bytes) or not isinstance(member_ids, Sequence):
            raise TypeError("member_ids must be a sequence of member IDs")
        members = list(member_ids)
        if len(members) != self._population_size:
            raise ValueError(
                f"member_ids must contain exactly {self._population_size} members"
            )
        for member_id in members:
            self._validate_member_id(member_id)
        if len(set(members)) != len(members):
            raise ValueError("member IDs must be unique")
        return sorted(members)

    @staticmethod
    def _validate_member_id(member_id: Any, *, label: str = "member IDs") -> None:
        if not isinstance(member_id, str) or not member_id:
            raise ValueError(f"{label} must be non-empty strings")

    @staticmethod
    def _generator(seed: int) -> random.Random:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        return random.Random(seed)
