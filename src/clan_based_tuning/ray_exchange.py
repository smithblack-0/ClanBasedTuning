"""Ray actor transport for the process-local ``ClanController`` callbacks.

The exchange stores plain completed-round records. It implements rendezvous and
winner-agreement coordination, but it does not choose a winner, mutate a member,
or execute Tune and Lightning lifecycle.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import ray

from clan_based_tuning.controller_types import ClanRound

__all__ = [
    "PublishedRound",
    "RayControllerCallbacks",
    "RayRoundExchange",
    "RoundExchange",
]


def _completed_round_cannot_publish(round_: ClanRound) -> None:
    raise RuntimeError("a loaded population record cannot publish fitness")


@dataclass(frozen=True, slots=True)
class PublishedRound:
    """Callback-free representation of one completed member round."""

    member_id: int
    round_index: int
    config: dict[str, float]
    fitness: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", dict(self.config))

    @classmethod
    def from_clan_round(cls, round_: ClanRound) -> PublishedRound:
        if round_.fitness is None:
            raise RuntimeError("cannot publish a Clan round without fitness")
        return cls(
            member_id=round_.member_id,
            round_index=round_.round_index,
            config=round_.get_config(),
            fitness=round_.fitness,
        )

    def to_clan_round(self) -> ClanRound:
        return ClanRound(
            member_id=self.member_id,
            round_index=self.round_index,
            config=self.config,
            fitness=self.fitness,
            save_member_fitness=_completed_round_cannot_publish,
        )


class RoundExchange:
    """Asynchronous storage and barriers for one fixed live Clan."""

    def __init__(self, *, member_ids: Iterable[int], timeout_s: float):
        supplied_member_ids = tuple(member_ids)
        self._member_ids = frozenset(supplied_member_ids)
        if len(self._member_ids) != len(supplied_member_ids):
            raise ValueError("round exchange member identities must be unique")
        if len(self._member_ids) < 2:
            raise ValueError("a round exchange requires at least two members")
        self._timeout_s = timeout_s
        self._rounds: dict[int, dict[int, PublishedRound]] = {}
        self._ready: dict[int, asyncio.Event] = {}
        self._winner_calls: dict[int, dict[int, int]] = {}
        self._closed_rounds: set[int] = set()

    async def publish(self, round_: PublishedRound) -> None:
        """Store one unique completed member result and release a full barrier."""

        self._require_open_round(round_.round_index)
        self._require_member(round_.member_id)
        members = self._rounds.setdefault(round_.round_index, {})
        if round_.member_id in members:
            raise RuntimeError("member published the same Clan round twice")

        members[round_.member_id] = round_
        if set(members) == self._member_ids:
            self._event(round_.round_index).set()

    async def load(self, round_index: int) -> list[PublishedRound]:
        """Wait for and return exactly one completed record per live member."""

        self._require_open_round(round_index)
        event = self._event(round_index)
        if set(self._rounds.get(round_index, {})) == self._member_ids:
            event.set()
        try:
            await asyncio.wait_for(event.wait(), timeout=self._timeout_s)
        except TimeoutError as error:
            present = set(self._rounds.get(round_index, {}))
            missing = sorted(self._member_ids - present)
            raise RuntimeError(
                f"Clan round {round_index} timed out waiting for members {missing}"
            ) from error

        members = self._rounds[round_index]
        return [members[member_id] for member_id in sorted(self._member_ids)]

    async def announce(self, *, round_index: int, member_id: int, winner_id: int) -> bool:
        """Record one local controller decision and close unanimous rounds."""

        self._require_open_round(round_index)
        self._require_member(member_id)
        self._require_member(winner_id)
        if set(self._rounds.get(round_index, {})) != self._member_ids:
            raise RuntimeError("winner announced before the completed population existed")

        calls = self._winner_calls.setdefault(round_index, {})
        if member_id in calls:
            raise RuntimeError("member announced the same Clan winner twice")
        if calls and winner_id not in set(calls.values()):
            raise RuntimeError("process-local Clan controllers disagree on the winner")

        calls[member_id] = winner_id
        if set(calls) != self._member_ids:
            return False

        self._closed_rounds.add(round_index)
        del self._rounds[round_index]
        del self._ready[round_index]
        del self._winner_calls[round_index]
        return True

    def _event(self, round_index: int) -> asyncio.Event:
        return self._ready.setdefault(round_index, asyncio.Event())

    def _require_member(self, member_id: int) -> None:
        if member_id not in self._member_ids:
            raise RuntimeError(f"member {member_id} is outside the live Clan")

    def _require_open_round(self, round_index: int) -> None:
        if round_index in self._closed_rounds:
            raise RuntimeError(f"Clan round {round_index} is already closed")


RayRoundExchange = ray.remote(RoundExchange)


class RayControllerCallbacks:
    """Bind one process-local controller to a Ray round-exchange actor."""

    def __init__(
        self,
        *,
        exchange: Any,
        member_id: int,
        resolve: Callable[[Any], Any] = ray.get,
    ):
        self._exchange = exchange
        self._member_id = member_id
        self._resolve = resolve
        self._loaded_round: int | None = None
        self._selected_winner: int | None = None

    def save_member_fitness(self, round_: ClanRound) -> None:
        if round_.member_id != self._member_id:
            raise RuntimeError("controller published another member's Clan round")
        self._resolve(self._exchange.publish.remote(PublishedRound.from_clan_round(round_)))

    def load_population(self, round_index: int) -> list[ClanRound]:
        if self._loaded_round is not None:
            raise RuntimeError("controller loaded another population before selecting a winner")
        published = self._resolve(self._exchange.load.remote(round_index))
        self._loaded_round = round_index
        return [round_.to_clan_round() for round_ in published]

    def select_winner(self, winner_id: int) -> None:
        if self._loaded_round is None:
            raise RuntimeError("controller selected a winner before loading the population")
        self._resolve(
            self._exchange.announce.remote(
                round_index=self._loaded_round,
                member_id=self._member_id,
                winner_id=winner_id,
            )
        )
        self._selected_winner = winner_id
        self._loaded_round = None

    def take_selected_winner(self) -> int:
        if self._selected_winner is None:
            raise RuntimeError("controller did not select a winner")
        winner_id = self._selected_winner
        self._selected_winner = None
        return winner_id
