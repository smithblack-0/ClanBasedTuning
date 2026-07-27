"""Process-group rendezvous for externally launched Ray Tune trial processes."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass

import ray

from clan_based_tuning.lightning_ddp import ClanProcessGroup
from clan_based_tuning.ray_exchange import RoundExchange

__all__ = [
    "ClanRuntimeExchange",
    "ProcessGroupRendezvous",
    "RayClanRuntimeExchange",
]


@dataclass(frozen=True, slots=True)
class _PendingMember:
    token: str
    host: str
    port: int | None


@dataclass(frozen=True, slots=True)
class _Session:
    session_id: int
    tokens: dict[int, str]
    master_address: str
    master_port: int


class ProcessGroupRendezvous:
    """Resolve one fresh cross-trial DDP session at a time."""

    def __init__(self, *, member_ids: Iterable[int], timeout_s: float):
        supplied_member_ids = tuple(member_ids)
        self._member_ids = frozenset(supplied_member_ids)
        if len(self._member_ids) != len(supplied_member_ids):
            raise ValueError("process-group member identities must be unique")
        if self._member_ids != frozenset(range(len(self._member_ids))):
            raise ValueError("process-group member identities must be contiguous ranks")
        if len(self._member_ids) < 2:
            raise ValueError("a process group requires at least two members")

        self._timeout_s = timeout_s
        self._pending: dict[int, _PendingMember] = {}
        self._ready = asyncio.Event()
        self._session: _Session | None = None
        self._returned: set[int] = set()
        self._used_tokens: set[str] = set()
        self._next_session_id = 0

    async def join(
        self,
        *,
        member_id: int,
        token: str,
        host: str,
        port: int | None,
    ) -> ClanProcessGroup:
        """Register one process instance and wait for a complete fresh session."""

        self._require_member(member_id)
        if not token:
            raise ValueError("process-group token must be non-empty")
        if token in self._used_tokens:
            raise RuntimeError("process-group token cannot be reused")
        if token in {pending.token for pending in self._pending.values()}:
            raise RuntimeError("process-group token already identifies another member")
        if not host:
            raise ValueError("process-group host must be non-empty")
        if member_id == 0 and port is None:
            raise ValueError("rank zero must publish the process-group port")
        if port is not None and not 0 < port < 65536:
            raise ValueError("process-group port must be valid")
        if member_id != 0 and port is not None:
            raise ValueError("only rank zero may publish the process-group port")
        if member_id in self._pending:
            raise RuntimeError("member joined the same process-group window twice")

        self._pending[member_id] = _PendingMember(token=token, host=host, port=port)
        if set(self._pending) == self._member_ids:
            rank_zero = self._pending[0]
            assert rank_zero.port is not None
            self._session = _Session(
                session_id=self._next_session_id,
                tokens={
                    pending_member: pending.token
                    for pending_member, pending in self._pending.items()
                },
                master_address=rank_zero.host,
                master_port=rank_zero.port,
            )
            self._ready.set()

        try:
            await asyncio.wait_for(self._ready.wait(), timeout=self._timeout_s)
        except TimeoutError as error:
            missing = sorted(self._member_ids - set(self._pending))
            raise RuntimeError(
                f"process-group rendezvous timed out waiting for members {missing}"
            ) from error

        session = self._session
        if session is None or session.tokens[member_id] != token:
            raise RuntimeError("member token does not belong to the completed session")
        process_group = ClanProcessGroup(
            session_id=session.session_id,
            global_rank=member_id,
            world_size=len(self._member_ids),
            master_address=session.master_address,
            master_port=session.master_port,
        )
        self._returned.add(member_id)
        if self._returned == self._member_ids:
            self._used_tokens.update(session.tokens.values())
            self._next_session_id += 1
            self._pending.clear()
            self._returned.clear()
            self._session = None
            self._ready = asyncio.Event()
        return process_group

    def _require_member(self, member_id: int) -> None:
        if member_id not in self._member_ids:
            raise RuntimeError(f"member {member_id} is outside the live Clan")


class ClanRuntimeExchange:
    """Ray actor composition root for independent Clan coordination state."""

    def __init__(self, *, member_ids: Iterable[int], timeout_s: float):
        member_ids = tuple(member_ids)
        self._rounds = RoundExchange(member_ids=member_ids, timeout_s=timeout_s)
        self._process_groups = ProcessGroupRendezvous(
            member_ids=member_ids,
            timeout_s=timeout_s,
        )

    async def publish(self, round_):
        return await self._rounds.publish(round_)

    async def load(self, round_index):
        return await self._rounds.load(round_index)

    async def announce(self, *, round_index, member_id, winner_id):
        return await self._rounds.announce(
            round_index=round_index,
            member_id=member_id,
            winner_id=winner_id,
        )

    async def join_process_group(self, *, member_id, token, host, port):
        return await self._process_groups.join(
            member_id=member_id,
            token=token,
            host=host,
            port=port,
        )


RayClanRuntimeExchange = ray.remote(ClanRuntimeExchange)
