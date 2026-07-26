"""Process-local Tune session for one Clan member."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from clan_based_tuning.controller_types import ClanRound
from clan_based_tuning.ray.rendezvous import _require_ray, resolve_tune_membership
from clan_based_tuning.spec import _metadata_from_trial_config


class ClanTuneSession:
    """Connect one Tune trial process to its fixed Clan membership.

    The session resolves the trial's DDP topology and owns only process-to-actor
    communication for completed ``ClanRound`` records. It does not select winners,
    save checkpoints, mutate optimizer values, or control Tune scheduling.
    """

    def __init__(self, trial_config: Mapping[str, Any]) -> None:
        self._clan = _metadata_from_trial_config(trial_config)
        self.runtime, self._handle = resolve_tune_membership(self._clan)

    @property
    def member_id(self) -> int:
        return self.runtime.global_rank

    @property
    def population_size(self) -> int:
        return self.runtime.world_size

    def save_member_fitness(self, round_: ClanRound) -> None:
        """Publish one completed local round to the named Ray actor."""

        ray = _require_ray()
        record = {
            "member_id": round_.member_id,
            "round_index": round_.round_index,
            "config": round_.get_config(),
            "fitness": round_.fitness,
        }
        ray.get(self._handle.submit_round.remote(self.runtime.trial_id, record))

    def load_population(self, round_index: int) -> list[ClanRound]:
        """Wait until every process has published the requested completed round."""

        ray = _require_ray()
        deadline = time.monotonic() + self._clan.rendezvous_timeout_s
        records = None
        while records is None and time.monotonic() < deadline:
            records = ray.get(
                self._handle.get_population.remote(self.runtime.trial_id, round_index)
            )
            if records is None:
                time.sleep(self._clan.rendezvous_poll_interval_s)
        if records is None:
            raise TimeoutError(
                f"Clan population did not complete round {round_index} before timeout"
            )
        return [
            ClanRound(
                member_id=int(record["member_id"]),
                round_index=int(record["round_index"]),
                config=dict(record["config"]),
                save_member_fitness=_discard_round,
                fitness=float(record["fitness"]),
            )
            for record in records
        ]


def _discard_round(round_: ClanRound) -> None:
    del round_
