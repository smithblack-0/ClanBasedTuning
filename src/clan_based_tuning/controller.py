"""Framework-independent per-process lifecycle for Clan Tuning.

One controller persists beside one training process. Its callbacks publish completed
rounds and load the completed Clan through an externally owned distributed
implementation. Checkpoint integration asks whether this process won, saves only that
winning state, loads the shared winning checkpoint into every next-generation process,
and then asks the controller to manufacture the local next round.
"""

import random
from collections.abc import Callable

from clan_based_tuning.controller_types import ClanRound, MutationSpec


class ClanController:
    """Progress one local member around the shared winner-checkpoint boundary.

    The controller owns fitness comparison and optimizer-configuration mutation. It
    does not own checkpoint creation, checkpoint transport, framework restoration, or
    process synchronization. The surrounding checkpoint lifecycle depends on this
    controller to learn whether the local process won and later calls ``advance()``
    only after the selected winner checkpoint has been loaded.
    """

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
        self._seed = seed
        self._save_member_fitness = save_member_fitness
        self._load_population = load_population
        self._winner_id = None
        self._winning_checkpoint_loaded = False
        self._round = ClanRound(
            member_id=member_id,
            round_index=0,
            config=initial_config,
            save_member_fitness=save_member_fitness,
        )

    @property
    def round_index(self):
        """Return the current completed-or-training round index."""

        return self._round.round_index

    @property
    def winner_id(self):
        """Return the cached current-round winner, or ``None`` before comparison."""

        return self._winner_id

    def get_config(self):
        """Return this process's controlled values for the current round."""

        return self._round.get_config()

    def set_fitness(self, fitness):
        """Publish this process's completed current round."""

        self._round.set_fitness(fitness)

    def is_round_winner(self):
        """Return whether this process owns the state selected for checkpointing.

        The population callback may block until all member results are available. The
        selected member ID is cached because checkpoint creation and later restoration
        belong to framework lifecycle code outside the controller.
        """

        if self._winner_id is None:
            rounds = self._load_completed_population()
            self._winner_id = self._find_winner(rounds).member_id
        return self.member_id == self._winner_id

    def advance(self):
        """Construct this process's next round from the loaded winning state.

        The supported integration reconstructs every next-generation Tune process from
        the same winner checkpoint. The restored winner member retains the selected
        optimizer configuration; every other member mutates it locally.
        """

        if self._winner_id is None:
            raise RuntimeError("the round winner must be resolved before advancing")
        if not self._winning_checkpoint_loaded:
            raise RuntimeError("the winning checkpoint must be loaded before advancing")

        next_round_index = self._round.round_index + 1
        config = self._round.get_config()
        if self.member_id != self._winner_id:
            config = self._mutate(config, next_round_index)

        self._round = ClanRound(
            member_id=self.member_id,
            round_index=next_round_index,
            config=config,
            save_member_fitness=self._save_member_fitness,
        )
        self._winner_id = None
        self._winning_checkpoint_loaded = False

    def state_dict(self):
        """Return controller state to place in the winner's framework checkpoint.

        The winner saves this state after selection and before mutation. The trial seed
        is intentionally absent: it belongs to the receiving process configuration,
        not to the common winning checkpoint.
        """

        return {
            "round_index": self._round.round_index,
            "config": self._round.get_config(),
            "fitness": self._round.fitness,
            "winner_id": self._winner_id,
        }

    def load_state_dict(self, state):
        """Load common winner state while preserving process-local identity and seed."""

        self._round = ClanRound(
            member_id=self.member_id,
            round_index=state["round_index"],
            config=state["config"],
            save_member_fitness=self._save_member_fitness,
            fitness=state["fitness"],
        )
        self._winner_id = state["winner_id"]
        self._winning_checkpoint_loaded = self._winner_id is not None

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

    def _mutate(self, base_values, round_index):
        random_stream = random.Random(f"{self._seed}:{self.member_id}:{round_index}")
        return {
            name: mutation.mutate(base_values[name], random_stream)
            for name, mutation in self._mutations.items()
        }
