"""Framework-independent per-process lifecycle for Clan Tuning.

One controller persists beside one training process. Its callbacks publish completed
rounds, load the completed Clan, and apply the selected winner through an externally
owned distributed implementation.
"""

import random
from collections.abc import Callable

from clan_based_tuning.controller_types import ClanRound, MutationSpec


class ClanController:
    """Advance one local clan member between training rounds."""

    def __init__(
        self,
        *,
        member_id: int,
        population_size: int,
        initial_config: dict[str, float],
        mutations: dict[str, MutationSpec],
        mode: str,
        seed: int,
        save_member_fitness: Callable[[ClanRound], None],
        load_population: Callable[[int], list[ClanRound]],
        select_winner: Callable[[int], None],
    ):
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        if not 0 <= member_id < population_size:
            raise ValueError("member_id must identify one member of the population")
        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")

        self.member_id = member_id
        self.population_size = population_size
        self._mutations = dict(mutations)
        self._mode = mode
        self._random = random.Random(f"{seed}:{member_id}")
        self._save_member_fitness = save_member_fitness
        self._load_population = load_population
        self._select_winner = select_winner
        self._round = ClanRound(
            member_id=member_id,
            round_index=0,
            config=initial_config,
            save_member_fitness=save_member_fitness,
        )

    def get_config(self):
        """Return this process's controlled values for the current round."""

        return self._round.get_config()

    def set_fitness(self, fitness):
        """Publish this process's completed current round."""

        self._round.set_fitness(fitness)

    def advance(self):
        """Adopt the winner and construct this process's next round.

        The load callback owns rendezvous and transport. The controller retains one
        corruption guard: it refuses to advance unless the callback returns exactly
        one completed record for every expected member and for the requested round.
        """

        rounds = self._load_completed_population()
        winner = self._find_winner(rounds)
        next_config = (
            winner.get_config()
            if self.member_id == winner.member_id
            else self._mutate(winner.config)
        )

        self._select_winner(winner.member_id)
        self._round = ClanRound(
            member_id=self.member_id,
            round_index=self._round.round_index + 1,
            config=next_config,
            save_member_fitness=self._save_member_fitness,
        )

    def state_dict(self):
        """Return the local state required to resume this controller."""

        return {
            "random_state": self._random.getstate(),
            "round_index": self._round.round_index,
            "config": self._round.get_config(),
            "fitness": self._round.fitness,
        }

    def load_state_dict(self, state):
        """Restore a state previously returned by ``state_dict``."""

        self._random.setstate(state["random_state"])
        self._round = ClanRound(
            member_id=self.member_id,
            round_index=state["round_index"],
            config=state["config"],
            save_member_fitness=self._save_member_fitness,
            fitness=state["fitness"],
        )

    def _load_completed_population(self):
        round_index = self._round.round_index
        rounds = self._load_population(round_index)
        expected_ids = set(range(self.population_size))
        actual_ids = {round_.member_id for round_ in rounds}

        if len(rounds) != self.population_size or actual_ids != expected_ids:
            raise RuntimeError("population is incomplete or contains duplicate members")
        if any(round_.round_index != round_index for round_ in rounds):
            raise RuntimeError("population contains results from the wrong round")
        if any(round_.fitness is None for round_ in rounds):
            raise RuntimeError("population contains a member without fitness")
        return rounds

    def _find_winner(self, rounds):
        if self._mode == "min":
            return min(rounds, key=lambda round_: (round_.fitness, round_.member_id))
        return max(rounds, key=lambda round_: (round_.fitness, -round_.member_id))

    def _mutate(self, base_values):
        return {
            name: mutation.mutate(base_values[name], self._random)
            for name, mutation in self._mutations.items()
        }
