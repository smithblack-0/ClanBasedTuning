"""Framework-independent population transition for Clan Tuning.

The named data contracts live in :mod:`clan_based_tuning.controller_types`.
``ClanController`` assumes those internal objects are trusted. It owns only the
selection, mutation, and random-stream transition between generations.
"""

import random

from clan_based_tuning.controller_types import (
    ControllerPolicy,
    Population,
    PopulationMember,
)


class ClanController:
    """Select one parent and produce the next trusted ``Population``."""

    def __init__(self, policy):
        if not isinstance(policy, ControllerPolicy):
            raise TypeError("policy must be a ControllerPolicy")
        self._policy = policy
        self._random = random.Random(policy.seed)

    @property
    def population_size(self):
        """Return the fixed number of ranks in this policy."""

        return self._policy.population_size

    def initial_population(self):
        """Create the first population from the policy defaults."""

        defaults = {
            name: mutation.default
            for name, mutation in self._policy.mutations.items()
        }
        members = {0: PopulationMember(defaults)}
        for rank in range(1, self.population_size):
            members[rank] = PopulationMember(self._mutate(defaults))
        return Population(members)

    def next_generation(self, population):
        """Select the sole parent and return the next population.

        The external lifecycle supplies one trusted ``Population`` of the configured
        size and attaches one fitness to every member. Milestone 3 owns validation
        of the framework data used to construct that population.
        """

        if not isinstance(population, Population):
            raise TypeError("population must be a Population")
        if len(population) != self.population_size:
            raise ValueError(
                f"population must contain exactly {self.population_size} ranks"
            )
        missing_ranks = population.missing_fitness_ranks()
        if missing_ranks:
            raise RuntimeError(
                f"population is missing fitness for ranks {missing_ranks}"
            )

        key = lambda rank: population.members[rank].fitness
        if self._policy.mode == "min":
            parent_rank = min(population.ranks, key=key)
        else:
            parent_rank = max(population.ranks, key=key)

        parent_values = population.members[parent_rank].hyperparameters
        members = {}
        for rank in population.ranks:
            values = (
                dict(parent_values)
                if rank == parent_rank
                else self._mutate(parent_values)
            )
            members[rank] = PopulationMember(values)
        return parent_rank, Population(members)

    def state_dict(self):
        """Return the random-stream state required for identical continuation."""

        return {"random_state": self._random.getstate()}

    def load_state_dict(self, state):
        """Restore a state previously returned by ``state_dict``."""

        self._random.setstate(state["random_state"])

    def _mutate(self, base_values):
        return {
            name: mutation.mutate(base_values[name], self._random)
            for name, mutation in self._policy.mutations.items()
        }
