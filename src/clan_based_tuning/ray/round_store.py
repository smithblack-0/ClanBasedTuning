"""Plain state for distributing one completed Clan population per round.

``CompletedRoundStore`` is deliberately independent of Ray. A later actor wrapper may
call it, but this class owns only the in-memory lifecycle of plain completed-round
records: collect one record per member, expose the same ordered population to every
member, and release the payload after every member has read it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


class CompletedRoundStore:
    """Collect and distribute one completed round for a fixed population.

    The store has no winner-selection, checkpoint, scheduling, polling, timeout, or
    process-identity authority. Callers supply an already resolved integer member ID.
    ``read_population`` returns ``None`` until every member has published the current
    round. Once complete, every member receives the same member-ordered snapshot.

    Only one logical round may be active. The final distinct reader releases its payload
    and advances the store to the next round. This matches the synchronous controller
    lifecycle and avoids retaining either old populations or an unbounded closed-round
    ledger.
    """

    def __init__(self, population_size: int) -> None:
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        self.population_size = population_size
        self._round_index = 0
        self._members: dict[int, dict[str, Any]] = {}
        self._readers: set[int] = set()

    def publish(self, member_id: int, record: Mapping[str, Any]) -> None:
        """Store one member's completed record for the current round."""

        self._validate_member_id(member_id)
        stored = self._copy_record(record)
        if stored["member_id"] != member_id:
            raise RuntimeError("completed record member does not match the publishing member")
        self._require_current_round(stored["round_index"])
        if member_id in self._members:
            raise RuntimeError("member published the same round more than once")
        self._members[member_id] = stored

    def read_population(
        self,
        member_id: int,
        round_index: int,
    ) -> list[dict[str, Any]] | None:
        """Return the complete ordered population, or ``None`` while it is incomplete.

        Repeated reads by the same member are idempotent while another member has not
        yet consumed the round. The final distinct reader advances the store.
        """

        self._validate_member_id(member_id)
        self._require_current_round(round_index)
        if len(self._members) != self.population_size:
            return None
        expected_ids = set(range(self.population_size))
        if set(self._members) != expected_ids:
            raise RuntimeError("completed round contains an invalid population")

        population = [
            self._copy_record(self._members[index]) for index in range(self.population_size)
        ]
        self._readers.add(member_id)
        if len(self._readers) == self.population_size:
            self._members.clear()
            self._readers.clear()
            self._round_index += 1
        return population

    def _validate_member_id(self, member_id: int) -> None:
        if not 0 <= member_id < self.population_size:
            raise ValueError("member_id must identify one member of the population")

    def _require_current_round(self, round_index: int) -> None:
        if round_index < self._round_index:
            raise RuntimeError("completed round is already closed")
        if round_index > self._round_index:
            raise RuntimeError("previous completed round has not closed")

    @staticmethod
    def _copy_record(record: Mapping[str, Any]) -> dict[str, Any]:
        member_id = record["member_id"]
        round_index = record["round_index"]
        config = record["config"]
        fitness = float(record["fitness"])

        if not isinstance(member_id, int):
            raise TypeError("completed record member_id must be an integer")
        if not isinstance(round_index, int):
            raise TypeError("completed record round_index must be an integer")
        if round_index < 0:
            raise ValueError("completed record round_index must be non-negative")
        if not isinstance(config, Mapping):
            raise TypeError("completed record config must be a mapping")
        if not math.isfinite(fitness):
            raise ValueError("completed record fitness must be finite")

        return {
            "member_id": member_id,
            "round_index": round_index,
            "config": dict(config),
            "fitness": fitness,
        }
