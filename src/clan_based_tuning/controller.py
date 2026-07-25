"""Framework-independent population policy for Clan Tuning.

The controller runs between training rounds. The caller owns the live members,
training, model and optimizer state, checkpoints, and framework lifecycle. It
passes two rank-ordered sequences to :meth:`ClanController.next_generation`:

``fitnesses[rank]``
    The comparable fitness produced by the external member at ``rank``.

``configurations[rank]``
    That member's optimizer-hyperparameter mapping. Every mapping contains exactly
    the names declared when the controller was constructed.

The controller returns the selected parent rank and one next optimizer-
hyperparameter mapping per rank. It never constructs an optimizer, transfers
state, manages a population runtime, or imports Ray or Lightning objects.
"""

import math
import random
from collections.abc import Mapping, Sequence

_SPEC_FIELDS = frozenset(
    {"default", "standard_deviation", "geometry", "minimum", "maximum"}
)


class ClanController:
    """Select one Clan parent and generate the next optimizer configurations.

    The controller owns only the evolutionary calculation. It stores immutable
    mutation policy and a private pseudorandom-number generator. External code
    remains responsible for deciding which live members form the complete input,
    gathering their fitness values and configurations, and applying the returned
    parent/configuration decision.

    Linear hyperparameters receive additive Gaussian perturbations. Logarithmic
    hyperparameters receive multiplicative log-normal perturbations. The selected
    parent's configuration is retained exactly at its rank; every other rank is
    mutated from that same parent configuration.
    """

    def __init__(self, *, hyperparameters, mode, seed):
        """Configure the population policy and its reproducible random stream.

        Parameters
        ----------
        hyperparameters:
            Mapping from optimizer-hyperparameter name to a specification mapping.
            Every specification contains exactly:

            ``default``
                Initial value before mutation.
            ``standard_deviation``
                Standard deviation of the Gaussian displacement. For ``linear``
                geometry this is measured in value units. For ``log`` geometry it
                is measured in natural-log units, so mutation multiplies by
                ``exp(Normal(0, standard_deviation))``.
            ``geometry``
                Either ``"linear"`` or ``"log"``.
            ``minimum`` and ``maximum``
                Inclusive legal bounds. Logarithmic bounds must be positive.
        mode:
            ``"min"`` selects the lowest fitness; ``"max"`` selects the highest.
            Equal fitness values select the lowest rank.
        seed:
            Seed used to initialize the controller's random stream. Controllers
            constructed with the same policy and seed remain identical when they
            receive the same valid calls in the same order.
        """

        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")

        self._hyperparameters = self._normalize_hyperparameters(hyperparameters)
        self._mode = mode
        self._random = random.Random(seed)

    def initial_configurations(self, population_size):
        """Return rank-ordered optimizer configurations for the first round.

        Preconditions
        -------------
        ``population_size`` is an integer of at least two.

        Postconditions
        --------------
        The result contains one new mapping per rank. Rank zero retains the exact
        declared defaults; every other rank is independently mutated from those
        defaults. Calling this method advances the controller's random stream.
        """

        if not isinstance(population_size, int):
            raise TypeError("population_size must be an integer")
        if population_size < 2:
            raise ValueError("population_size must be at least two")

        defaults = {
            name: specification["default"]
            for name, specification in self._hyperparameters.items()
        }
        configurations = [dict(defaults)]
        for _ in range(1, population_size):
            configurations.append(self._mutate(defaults))
        return configurations

    def next_generation(self, fitnesses, configurations):
        """Select the sole parent and return rank-ordered next configurations.

        ``fitnesses[rank]`` and ``configurations[rank]`` must describe the same
        external member. The two sequences must have equal length and contain at
        least two ranks. The caller is responsible for supplying the complete live
        Clan; this method verifies the internal alignment and legality of the data
        it receives but does not own framework population membership.

        The complete input is normalized before any random numbers are consumed.
        On success, the selected parent rank retains an exact copy of its current
        optimizer configuration. Every other rank receives an independent mutation
        of that parent configuration. Input sequences and mappings are not changed.
        """

        fitnesses = self._normalize_fitnesses(fitnesses)
        configurations = self._normalize_configurations(configurations)
        if len(fitnesses) != len(configurations):
            raise ValueError("fitnesses and configurations must have equal length")
        if len(fitnesses) < 2:
            raise ValueError("a generation must contain at least two ranks")

        if self._mode == "min":
            parent_rank = min(range(len(fitnesses)), key=fitnesses.__getitem__)
        else:
            parent_rank = max(range(len(fitnesses)), key=fitnesses.__getitem__)

        parent = configurations[parent_rank]
        next_configurations = []
        for rank in range(len(configurations)):
            if rank == parent_rank:
                next_configurations.append(dict(parent))
            else:
                next_configurations.append(self._mutate(parent))
        return parent_rank, next_configurations

    def state_dict(self):
        """Return the random-stream state required to resume identical mutation.

        Mutation policy is constructor configuration, not evolving state. External
        persistence should therefore recreate the same controller policy and load
        this returned state before the next evolutionary call.
        """

        return {"random_state": self._random.getstate()}

    def load_state_dict(self, state):
        """Restore a state previously returned by :meth:`state_dict`.

        The mapping must contain ``random_state``. Python's ``random.Random``
        validates the state representation and raises when it is incompatible.
        """

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
                candidate = value * math.exp(displacement)
            mutated[name] = min(
                max(candidate, specification["minimum"]),
                specification["maximum"],
            )
        return mutated

    def _normalize_fitnesses(self, fitnesses):
        if isinstance(fitnesses, str | bytes) or not isinstance(fitnesses, Sequence):
            raise TypeError("fitnesses must be a rank-ordered sequence")
        return [
            self._finite_float(fitness, f"fitness at rank {rank}")
            for rank, fitness in enumerate(fitnesses)
        ]

    def _normalize_configurations(self, configurations):
        if isinstance(configurations, str | bytes) or not isinstance(configurations, Sequence):
            raise TypeError("configurations must be a rank-ordered sequence")
        return [
            self._normalize_configuration(configuration, rank)
            for rank, configuration in enumerate(configurations)
        ]

    def _normalize_configuration(self, configuration, rank):
        if not isinstance(configuration, Mapping):
            raise TypeError(f"configuration at rank {rank} must be a mapping")
        if set(configuration) != set(self._hyperparameters):
            raise ValueError(
                f"configuration at rank {rank} must contain exactly the declared "
                "optimizer hyperparameters"
            )

        normalized = {}
        for name, specification in self._hyperparameters.items():
            value = self._finite_float(
                configuration[name],
                f"hyperparameter {name!r} at rank {rank}",
            )
            if not specification["minimum"] <= value <= specification["maximum"]:
                raise ValueError(
                    f"hyperparameter {name!r} at rank {rank} must be within "
                    f"[{specification['minimum']}, {specification['maximum']}]"
                )
            normalized[name] = value
        return normalized

    @classmethod
    def _normalize_hyperparameters(cls, hyperparameters):
        if not isinstance(hyperparameters, Mapping) or not hyperparameters:
            raise ValueError("hyperparameters must be a non-empty mapping")

        normalized = {}
        for name in sorted(hyperparameters):
            specification = hyperparameters[name]
            if not isinstance(name, str) or not name:
                raise ValueError("hyperparameter names must be non-empty strings")
            if not isinstance(specification, Mapping):
                raise TypeError(f"specification for {name!r} must be a mapping")
            if set(specification) != _SPEC_FIELDS:
                raise ValueError(
                    f"specification for {name!r} must contain exactly default, "
                    "standard_deviation, geometry, minimum, and maximum"
                )

            default = cls._finite_float(specification["default"], f"default for {name!r}")
            standard_deviation = cls._finite_float(
                specification["standard_deviation"],
                f"standard_deviation for {name!r}",
            )
            minimum = cls._finite_float(specification["minimum"], f"minimum for {name!r}")
            maximum = cls._finite_float(specification["maximum"], f"maximum for {name!r}")
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

            normalized[name] = {
                "default": default,
                "standard_deviation": standard_deviation,
                "geometry": geometry,
                "minimum": minimum,
                "maximum": maximum,
            }
        return normalized

    @staticmethod
    def _finite_float(value, label):
        try:
            value = float(value)
        except (TypeError, ValueError) as error:
            raise TypeError(f"{label} must be a real scalar") from error
        if not math.isfinite(value):
            raise ValueError(f"{label} must be finite")
        return value
