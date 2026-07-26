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
    """Collect and distribute completed-round records for one fixed population.

    The store has no winner-selection, checkpoint, scheduling, polling, timeout, or
    process-identity authority. Callers supply an already resolved integer member ID.
    ``read_population`` returns ``None`` until every member has published the requested
    round. Once complete, every member receives the same member-ordered snapshot.

    A round closes after every member has read it. Closing releases the stored payload
    while retaining enough lifecycle state to reject late duplicate publication or
    consumption of an already-finished round.
    """

    def __init__(self, population_size: int) -> None:
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        self.population_size = population_size
        self._rounds: dict[int, dict[int, dict[str, Any]]] = {}
        self._readers: dict[int, set[int]] = {}
        self._closed_rounds: set[int] = set()

    def publish(self, member_id: int, record: Mapping[str, Any]) -> None:
        """Store one member's completed record for its declared round."""

        self._validate_member_id(member_id)
        stored = self._copy_record(record)
        round_index = stored["round_index"]
        if stored["member_id"] != member_id:
            raise RuntimeError("completed record member does not match the publishing member")
        if round_index in self._closed_rounds:
            raise RuntimeError("completed round is already closed")

        members = self._rounds.setdefault(round_index, {})
        if member_id in members:
            raise RuntimeError("member published the same round more than once")
        members[member_id] = stored

    def read_population(
        self,
        member_id: int,
        round_index: int,
    ) -> list[dict[str, Any]] | None:
        """Return the complete ordered population, or ``None`` while it is incomplete.

        Repeated reads by the same member are idempotent while another member has not
        yet consumed the round. The final distinct reader closes the round.
        """

        self._validate_member_id(member_id)
        if round_index in self._closed_rounds:
            raise RuntimeError("completed round is already closed")
        if round_index not in self._rounds:
            return None

        members = self._rounds[round_index]
        if len(members) != self.population_size:
            return None
        expected_ids = set(range(self.population_size))
        if set(members) != expected_ids:
            raise RuntimeError("completed round contains an invalid population")

        population = [self._copy_record(members[index]) for index in range(self.population_size)]
        readers = self._readers.setdefault(round_index, set())
        readers.add(member_id)
        if len(readers) == self.population_size:
            del self._rounds[round_index]
            del self._readers[round_index]
            self._closed_rounds.add(round_index)
        return population

    def _validate_member_id(self, member_id: int) -> None:
        if not 0 <= member_id < self.population_size:
            raise ValueError("member_id must identify one member of the population")

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
