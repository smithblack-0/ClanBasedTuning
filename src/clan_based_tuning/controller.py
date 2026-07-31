"""Framework-independent per-process lifecycle for Clan Tuning.

One controller persists beside one training process. Its callbacks publish completed
rounds, load the completed Clan, and expose the selected continuation through an
externally owned distributed implementation.
"""

import random
from collections.abc import Callable

from clan_based_tuning.controller_types import ClanRound, MutationSpec


class ClanController:
    """Close one local round, restore the winner, and create the next round."""

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
        self._selected_winner = None
        self._selection_restored = False

    def get_config(self):
        """Return this process's controlled values for the current round."""

        return self._round.get_config()

    def set_fitness(self, fitness):
        """Publish this process's completed current round."""

        self._round.set_fitness(fitness)

    def close_round(self):
        """Select the completed winner without manufacturing the next round.

        The selected completed round is checkpointed with the controller. A new round
        can be created only after that state has been restored into a receiving member.
        """

        if self._selected_winner is not None:
            raise RuntimeError("current round is already closed")

        rounds = self._load_completed_population()
        winner = self._find_winner(rounds)
        self._selected_winner = self._copy_round(winner)
        self._select_winner(winner.member_id)
        return self.member_id == winner.member_id

    def start_next_round(self):
        """Rebase restored winner state and manufacture this member's next round."""

        if self._selected_winner is None:
            raise RuntimeError("current round has not been closed")
        if not self._selection_restored:
            raise RuntimeError("winning round must be restored before starting the next round")

        winner = self._selected_winner
        next_round_index = winner.round_index + 1
        self._random = self._rebase_random()
        next_config = (
            winner.get_config()
            if self.member_id == winner.member_id
            else self._mutate(winner.config)
        )
        self._round = ClanRound(
            member_id=self.member_id,
            round_index=next_round_index,
            config=next_config,
            save_member_fitness=self._save_member_fitness,
        )
        self._selected_winner = None
        self._selection_restored = False

    def state_dict(self):
        """Return the state required to checkpoint this controller lifecycle."""

        return {
            "random_state": self._random.getstate(),
            "round_index": self._round.round_index,
            "config": self._round.get_config(),
            "fitness": self._round.fitness,
            "selected_winner": self._round_state(self._selected_winner),
        }

    def load_state_dict(self, state):
        """Restore winner-derived state while preserving the receiving member ID."""

        self._random.setstate(state["random_state"])
        self._round = ClanRound(
            member_id=self.member_id,
            round_index=state["round_index"],
            config=state["config"],
            save_member_fitness=self._save_member_fitness,
            fitness=state["fitness"],
        )
        selected_winner = state["selected_winner"]
        self._selected_winner = (
            None
            if selected_winner is None
            else ClanRound(
                member_id=selected_winner["member_id"],
                round_index=selected_winner["round_index"],
                config=selected_winner["config"],
                save_member_fitness=self._save_member_fitness,
                fitness=selected_winner["fitness"],
            )
        )
        self._selection_restored = self._selected_winner is not None

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

    def _rebase_random(self):
        rebased = random.Random()
        rebased.setstate(self._random.getstate())
        for _ in range(self.member_id + 1):
            rebased.random()
        return rebased

    def _mutate(self, base_values):
        return {
            name: mutation.mutate(base_values[name], self._random)
            for name, mutation in self._mutations.items()
        }

    def _copy_round(self, round_):
        return ClanRound(
            member_id=round_.member_id,
            round_index=round_.round_index,
            config=round_.config,
            save_member_fitness=self._save_member_fitness,
            fitness=round_.fitness,
        )

    @staticmethod
    def _round_state(round_):
        if round_ is None:
            return None
        return {
            "member_id": round_.member_id,
            "round_index": round_.round_index,
            "config": round_.get_config(),
            "fitness": round_.fitness,
        }
