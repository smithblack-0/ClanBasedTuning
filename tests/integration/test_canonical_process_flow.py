"""Executable specification of the Clan round transition.

The fakes in this test replace storage and numerical training, not lifecycle
ordering. Each controller still runs beside one concurrent member process and
reaches the winner callback independently.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from clan_based_tuning import ClanController, MutationSpec


class RoundStore:
    """Publish local results and return one completed population by round."""

    def __init__(self, population_size):
        self.population_size = population_size
        self._rounds = {}
        self._lock = threading.Lock()

    def save(self, round_):
        with self._lock:
            self._rounds[(round_.round_index, round_.member_id)] = round_

    def load(self, round_index):
        with self._lock:
            return [
                self._rounds[(round_index, member_id)]
                for member_id in range(self.population_size)
                if (round_index, member_id) in self._rounds
            ]


@dataclass(frozen=True)
class TrainingCheckpoint:
    reference: str
    model_value: float
    optimizer_velocity: float


class WinningCheckpointStore:
    """Publish exactly one winner checkpoint and release waiting members."""

    def __init__(self):
        self._condition = threading.Condition()
        self._checkpoints = {}
        self.save_calls = []

    def save_winner(self, round_index, member_id, model_value, optimizer_velocity):
        reference = f"round-{round_index}-member-{member_id}"
        checkpoint = TrainingCheckpoint(
            reference=reference,
            model_value=model_value,
            optimizer_velocity=optimizer_velocity,
        )
        with self._condition:
            if round_index in self._checkpoints:
                raise RuntimeError(f"round {round_index} already has a winner checkpoint")
            self._checkpoints[round_index] = checkpoint
            self.save_calls.append((round_index, member_id))
            self._condition.notify_all()

    def wait_for_winner(self, round_index):
        with self._condition:
            ready = self._condition.wait_for(lambda: round_index in self._checkpoints, 2.0)
            if not ready:
                raise RuntimeError(f"winner checkpoint for round {round_index} was not ready")
            return self._checkpoints[round_index]


class MemberProcess:
    """Minimal process-local training state surrounding one Clan controller."""

    def __init__(self, member_id, population_size, rounds, checkpoints):
        self.member_id = member_id
        self.model_value = 10.0
        self.optimizer_velocity = 0.0
        self.learning_rate = 0.1 * (member_id + 1)
        self.selected_winners = []
        self.loaded_references = []
        self.controller = ClanController(
            member_id=member_id,
            population_size=population_size,
            initial_config={"lr": self.learning_rate},
            mutations={
                "lr": MutationSpec(
                    standard_deviation=0.025,
                    geometry="linear",
                    minimum=0.01,
                    maximum=1.0,
                )
            },
            mode="min",
            seed=41,
            save_member_fitness=rounds.save,
            load_population=rounds.load,
            select_winner=lambda winner_id: self._load_winner(
                checkpoints,
                winner_id,
            ),
        )

    def train(self, shared_gradient):
        """Apply one common gradient through member-local optimizer state."""

        self.optimizer_velocity = 0.9 * self.optimizer_velocity + shared_gradient
        self.model_value -= self.learning_rate * self.optimizer_velocity

    def report(self, fitness):
        self.controller.set_fitness(fitness)

    def advance(self):
        self.controller.advance()
        self.learning_rate = self.controller.get_config()["lr"]

    def _load_winner(self, checkpoints, winner_id):
        round_index = self.controller.state_dict()["round_index"]
        self.selected_winners.append(winner_id)
        if self.member_id == winner_id:
            checkpoints.save_winner(
                round_index,
                self.member_id,
                self.model_value,
                self.optimizer_velocity,
            )
        checkpoint = checkpoints.wait_for_winner(round_index)
        self.loaded_references.append(checkpoint.reference)
        self.model_value = checkpoint.model_value
        self.optimizer_velocity = checkpoint.optimizer_velocity


def _advance_concurrently(members):
    errors = []

    def advance(member):
        try:
            member.advance()
        except BaseException as error:  # pragma: no cover - re-raised in the test thread
            errors.append(error)

    threads = [threading.Thread(target=advance, args=(member,)) for member in members]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3.0)

    assert not [thread for thread in threads if thread.is_alive()]
    if errors:
        raise errors[0]


def test_members_repeat_winner_checkpoint_restore_and_local_configuration():
    """Two rounds use one parent state while retaining member-local next configs."""

    population_size = 3
    rounds = RoundStore(population_size)
    checkpoints = WinningCheckpointStore()
    members = [
        MemberProcess(member_id, population_size, rounds, checkpoints)
        for member_id in range(population_size)
    ]

    for member in members:
        member.train(shared_gradient=2.0)
    assert len({member.model_value for member in members}) == population_size

    for member, fitness in zip(members, [3.0, 1.0, 2.0], strict=True):
        member.report(fitness)
    _advance_concurrently(members)

    assert checkpoints.save_calls == [(0, 1)]
    assert [member.selected_winners for member in members] == [[1], [1], [1]]
    assert [member.loaded_references for member in members] == [
        ["round-0-member-1"],
        ["round-0-member-1"],
        ["round-0-member-1"],
    ]
    assert len({member.model_value for member in members}) == 1
    assert len({member.optimizer_velocity for member in members}) == 1
    assert members[1].learning_rate == 0.2
    assert len({member.learning_rate for member in members}) == population_size

    for member in members:
        member.train(shared_gradient=-1.5)
    assert len({member.model_value for member in members}) == population_size

    for member, fitness in zip(members, [0.5, 1.5, 2.5], strict=True):
        member.report(fitness)
    _advance_concurrently(members)

    assert checkpoints.save_calls == [(0, 1), (1, 0)]
    assert [member.selected_winners for member in members] == [[1, 0], [1, 0], [1, 0]]
    assert [member.loaded_references[-1] for member in members] == [
        "round-1-member-0",
        "round-1-member-0",
        "round-1-member-0",
    ]
    assert len({member.model_value for member in members}) == 1
    assert len({member.optimizer_velocity for member in members}) == 1
    assert len({member.learning_rate for member in members}) == population_size
