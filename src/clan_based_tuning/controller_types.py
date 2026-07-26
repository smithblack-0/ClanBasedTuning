"""Named data contracts used by the framework-independent Clan controller.

These types describe what controller data means. They do not describe where
framework data comes from or claim ownership of an optimizer configuration.
Milestone 3 orchestration translates and validates external framework state before
constructing these trusted controller-side objects.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MutationSpec:
    """Initialization and local mutation policy for one named hyperparameter.

    The key in ``ControllerPolicy.mutations`` supplies the hyperparameter name.
    This object owns only that value's initialization, mutation, and bounds.
    """

    default: float
    standard_deviation: float
    geometry: str
    minimum: float
    maximum: float

    def __post_init__(self):
        values = (
            self.default,
            self.standard_deviation,
            self.minimum,
            self.maximum,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("mutation values must be finite")
        if self.standard_deviation <= 0:
            raise ValueError("standard_deviation must be positive")
        if self.geometry not in {"linear", "log"}:
            raise ValueError("geometry must be 'linear' or 'log'")
        if self.minimum >= self.maximum:
            raise ValueError("minimum must be less than maximum")
        if not self.minimum <= self.default <= self.maximum:
            raise ValueError("default must be within bounds")
        if self.geometry == "log" and self.minimum <= 0:
            raise ValueError("log mutation requires positive bounds")

    def mutate(self, value, random_stream):
        """Return one bounded mutation of ``value``."""

        displacement = random_stream.gauss(0.0, self.standard_deviation)
        if self.geometry == "linear":
            candidate = value + displacement
        else:
            try:
                candidate = value * math.exp(displacement)
            except OverflowError:
                candidate = math.inf
        return min(max(candidate, self.minimum), self.maximum)


@dataclass(frozen=True, slots=True)
class ControllerPolicy:
    """Immutable settings required to evolve one fixed-size population."""

    population_size: int
    mutations: dict
    mode: str
    seed: int

    def __post_init__(self):
        if self.population_size < 2:
            raise ValueError("population_size must be at least two")
        if not self.mutations:
            raise ValueError("mutations must be non-empty")
        if self.mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")
        if any(not isinstance(item, MutationSpec) for item in self.mutations.values()):
            raise TypeError("mutations values must be MutationSpec objects")
        object.__setattr__(self, "mutations", dict(self.mutations))


@dataclass(slots=True)
class PopulationMember:
    """Controller-side data for one rank in one generation.

    ``hyperparameters`` contains only the named values evolved by the controller.
    It is not a full optimizer configuration and does not encode where those values
    came from. ``fitness`` remains absent until the external lifecycle reports it.
    """

    hyperparameters: dict
    fitness: float | None = None

    def __post_init__(self):
        if not isinstance(self.hyperparameters, dict):
            raise TypeError("hyperparameters must be a dictionary")
        self.hyperparameters = dict(self.hyperparameters)
        if self.fitness is not None:
            self.set_fitness(self.fitness)

    def set_fitness(self, value):
        """Record the comparable fitness reported for this member."""

        if not math.isfinite(value):
            raise ValueError("fitness must be finite")
        self.fitness = float(value)


@dataclass(slots=True)
class Population:
    """One complete generation keyed by stable controller rank.

    ``members`` maps contiguous integer ranks to ``PopulationMember`` objects. The
    member objects are trusted after construction; the controller does not inspect
    their hyperparameter dictionaries on every transition.
    """

    members: dict

    def __post_init__(self):
        if not isinstance(self.members, dict):
            raise TypeError("members must be a dictionary keyed by rank")
        if tuple(sorted(self.members)) != tuple(range(len(self.members))):
            raise ValueError("population ranks must be contiguous from zero")
        if any(not isinstance(item, PopulationMember) for item in self.members.values()):
            raise TypeError("members values must be PopulationMember objects")
        self.members = dict(self.members)

    def __len__(self):
        return len(self.members)

    @property
    def ranks(self):
        """Return the stable rank order for this generation."""

        return range(len(self.members))

    def set_fitness(self, rank, value):
        """Attach one reported fitness to the member at ``rank``."""

        self.members[rank].set_fitness(value)

    def missing_fitness_ranks(self):
        """Return ranks whose members have not reported fitness."""

        return tuple(rank for rank in self.ranks if self.members[rank].fitness is None)
