"""Framework-independent population policy for Clan Tuning.

Data contracts
--------------
Hyperparameter policy
    ``dict[name, specification]`` where every specification contains ``default``,
    ``standard_deviation``, ``geometry``, ``minimum``, and ``maximum``. The
    controller validates this immutable policy once during construction.

Optimizer configuration
    ``dict[name, value]`` containing the optimizer hyperparameters controlled by
    the policy. Controller-generated configurations satisfy the policy. A future
    framework adapter owns validating externally gathered configurations before it
    constructs a :class:`Population`.

Population
    A rank-indexed generation represented by :class:`Population`.
    ``population.configurations[rank]`` is that member's optimizer configuration;
    ``population.fitness[rank]`` is present only after that rank reports fitness.
    Population structure is validated once when the object is constructed. The
    controller then treats the object as trusted internal data.

The controller owns selection, local mutation, and its random stream. It does not
own live trials, training, model or optimizer state, checkpoints, distributed
communication, or framework lifecycle.
"""

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Real

_HYPERPARAMETER_SPEC_FIELDS = frozenset(
    {"default", "standard_deviation", "geometry", "minimum", "maximum"}
)


def _require_population_size(population_size):
    """Validate the immutable number of ranks in one Clan population."""

    if isinstance(population_size, bool) or not isinstance(population_size, int):
        raise TypeError("population_size must be an integer")
    if population_size < 2:
        raise ValueError("population_size must be at least two")
    return population_size


def _require_finite_real(value, label):
    """Return a finite float for one scalar boundary value."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label} must be a real scalar")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def _validate_hyperparameter_policy(hyperparameters):
    """Validate and copy the immutable optimizer-hyperparameter policy once."""

    if not isinstance(hyperparameters, Mapping):
        raise TypeError("hyperparameters must be a mapping")
    if not hyperparameters:
        raise ValueError("hyperparameters must be non-empty")

    names = list(hyperparameters)
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("hyperparameter names must be non-empty strings")

    policy = {}
    for name in sorted(names):
        specification = hyperparameters[name]
        if not isinstance(specification, Mapping):
            raise TypeError(f"specification for {name!r} must be a mapping")
        if set(specification) != _HYPERPARAMETER_SPEC_FIELDS:
            raise ValueError(
                f"specification for {name!r} must contain exactly default, "
                "standard_deviation, geometry, minimum, and maximum"
            )

        default = _require_finite_real(specification["default"], f"default for {name!r}")
        standard_deviation = _require_finite_real(
            specification["standard_deviation"],
            f"standard_deviation for {name!r}",
        )
        minimum = _require_finite_real(specification["minimum"], f"minimum for {name!r}")
        maximum = _require_finite_real(specification["maximum"], f"maximum for {name!r}")
        geometry = specification["geometry"]

        if standard_deviation <= 0.0:
            raise ValueError(f"standard_deviation for {name!r} must be positive")
        if geometry not in {"linear", "log"}:
            raise ValueError(f"geometry for {name!r} must be 'linear' or 'log'")
        if minimum >= maximum:
            raise ValueError(f"minimum for {name!r} must be less than maximum")
        if not minimum <= default <= maximum:
            raise ValueError(f"default for {name!r} must be within its bounds")
        if geometry == "log" and minimum <= 0.0:
            raise ValueError(f"log hyperparameter {name!r} requires positive bounds")

        policy[name] = {
            "default": default,
            "standard_deviation": standard_deviation,
            "geometry": geometry,
            "minimum": minimum,
            "maximum": maximum,
        }
    return policy


def _copy_population_configurations(configurations):
    """Validate one Population's rank/configuration structure and take ownership."""

    if not isinstance(configurations, dict):
        raise TypeError("configurations must be a dictionary keyed by rank")
    expected_ranks = set(range(len(configurations)))
    if set(configurations) != expected_ranks:
        raise ValueError("configuration ranks must be contiguous from zero")
    if not configurations:
        raise ValueError("a population must contain at least one rank")

    copied = {}
    for rank in range(len(configurations)):
        configuration = configurations[rank]
        if not isinstance(configuration, dict):
            raise TypeError(f"configuration for rank {rank} must be a dictionary")
        copied[rank] = dict(configuration)
    return copied


@dataclass(slots=True)
class Population:
    """One complete, rank-indexed generation of controller data.

    ``configurations`` is a dictionary whose keys are exactly ``0`` through
    ``len(population) - 1``. Each value is that rank's optimizer-hyperparameter
    dictionary. ``fitness`` is another rank-keyed dictionary; a missing key means
    the member has not reported fitness for the current generation.

    Construction validates this outer structure once and copies the supplied
    dictionaries. It deliberately does not revalidate hyperparameter names, bounds,
    or framework membership. Controller-generated populations already satisfy the
    policy, while Milestone 3 orchestration must validate externally gathered data
    before constructing a Population.
    """

    configurations: dict
    fitness: dict = field(default_factory=dict)

    def __post_init__(self):
        self.configurations = _copy_population_configurations(self.configurations)
        if not isinstance(self.fitness, dict):
            raise TypeError("fitness must be a dictionary keyed by rank")
        supplied_fitness = dict(self.fitness)
        self.fitness = {}
        for rank, value in supplied_fitness.items():
            self.set_fitness(rank, value)

    @property
    def ranks(self):
        """Return the stable rank order for this generation."""

        return range(len(self.configurations))

    def __len__(self):
        return len(self.configurations)

    def get_configuration(self, rank):
        """Return a copy of the optimizer configuration for ``rank``."""

        return dict(self.configurations[rank])

    def set_fitness(self, rank, value):
        """Record one member's finite fitness for the current generation."""

        if rank not in self.configurations:
            raise KeyError(f"unknown population rank {rank}")
        self.fitness[rank] = _require_finite_real(value, f"fitness for rank {rank}")

    def get_fitness(self, rank):
        """Return ``rank`` fitness, failing if that member has not reported yet."""

        try:
            return self.fitness[rank]
        except KeyError as error:
            raise RuntimeError(f"fitness for rank {rank} has not been set") from error

    def missing_fitness_ranks(self):
        """Return ranks that have not reported fitness for this generation."""

        return tuple(rank for rank in self.ranks if rank not in self.fitness)


class ClanController:
    """Select one parent and produce the next trusted Population.

    Construction owns immutable policy validation: population size, mutation
    policy, metric direction, and random-stream setup. ``next_generation`` accepts
    only a :class:`Population` matching that size, requires all fitness values to
    be present, then performs selection and mutation without re-auditing every
    configuration value.
    """

    def __init__(self, *, population_size, hyperparameters, mode, seed):
        """Configure one reproducible evolutionary policy.

        ``population_size`` is fixed for the controller lifetime. ``hyperparameters``
        follows the module-level Hyperparameter policy contract. ``mode`` is
        ``"min"`` or ``"max"``; equal fitness values select the lowest rank.
        ``seed`` is an integer used to create the private random stream.
        """

        self._population_size = _require_population_size(population_size)
        self._hyperparameters = _validate_hyperparameter_policy(hyperparameters)
        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        self._mode = mode
        self._random = random.Random(seed)

    @property
    def population_size(self):
        """Return the fixed number of ranks expected by this policy."""

        return self._population_size

    def initial_population(self):
        """Create the first Population with defaults retained at rank zero."""

        defaults = {
            name: specification["default"] for name, specification in self._hyperparameters.items()
        }
        configurations = {0: dict(defaults)}
        for rank in range(1, self._population_size):
            configurations[rank] = self._mutate(defaults)
        return Population(configurations)

    def next_generation(self, population):
        """Select the sole parent and return the next Population.

        The population must be a structurally valid :class:`Population` with the
        controller's fixed size and one fitness value per rank. Those are the only
        call-time checks. Configuration legality is a construction/integration
        boundary responsibility, not a repeated hot-path audit.
        """

        if not isinstance(population, Population):
            raise TypeError("population must be a Population")
        if len(population) != self._population_size:
            raise ValueError(f"population must contain exactly {self._population_size} ranks")
        missing_ranks = population.missing_fitness_ranks()
        if missing_ranks:
            raise RuntimeError(f"population is missing fitness for ranks {missing_ranks}")

        if self._mode == "min":
            parent_rank = min(population.ranks, key=population.get_fitness)
        else:
            parent_rank = max(population.ranks, key=population.get_fitness)

        parent = population.configurations[parent_rank]
        configurations = {}
        for rank in population.ranks:
            configurations[rank] = dict(parent) if rank == parent_rank else self._mutate(parent)
        return parent_rank, Population(configurations)

    def state_dict(self):
        """Return the random-stream state required to resume identical mutation."""

        return {"random_state": self._random.getstate()}

    def load_state_dict(self, state):
        """Restore a state previously returned by :meth:`state_dict`."""

        self._random.setstate(state["random_state"])

    def _mutate(self, base_configuration):
        mutated = {}
        for name, specification in self._hyperparameters.items():
            value = base_configuration[name]
            displacement = self._random.gauss(
                0.0,
                specification["standard_deviation"],
            )
            if specification["geometry"] == "linear":
                candidate = value + displacement
            else:
                try:
                    candidate = value * math.exp(displacement)
                except OverflowError:
                    candidate = math.inf
            mutated[name] = min(
                max(candidate, specification["minimum"]),
                specification["maximum"],
            )
        return mutated
