"""Ray rendezvous for Tune trials forming one Clan process group and round."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from clan_based_tuning.lightning.environment import _ClanRuntime
from clan_based_tuning.spec import _ClanMetadata


@dataclass(frozen=True, slots=True)
class _PendingMember:
    token: str
    host: str
    port: int | None


@dataclass(frozen=True, slots=True)
class _Session:
    session_id: int
    tokens: dict[str, str]
    master_address: str
    master_port: int


class RoundResultState:
    """Collect plain completed-round records from one fixed process population.

    This state has no model, checkpoint, scheduling, or winner-selection authority.
    Each Tune trial publishes one record and polls until the complete population is
    available. The per-process ``ClanController`` then performs the policy decision.
    """

    def __init__(self, population_size: int) -> None:
        self.population_size = population_size
        self._rounds: dict[int, dict[int, dict[str, Any]]] = {}

    def submit(self, member_id: int, record: dict[str, Any]) -> None:
        round_index = int(record["round_index"])
        record_member_id = int(record["member_id"])
        if record_member_id != member_id:
            raise RuntimeError("reported ClanRound member does not match the Tune trial rank")
        members = self._rounds.setdefault(round_index, {})
        if member_id in members:
            raise RuntimeError("a Clan member reported the same round more than once")
        members[member_id] = dict(record)

    def get_population(self, round_index: int) -> list[dict[str, Any]] | None:
        members = self._rounds.get(round_index)
        if members is None or len(members) != self.population_size:
            return None
        expected_ids = set(range(self.population_size))
        if set(members) != expected_ids:
            raise RuntimeError("completed round contains an invalid Clan membership")
        return [dict(members[member_id]) for member_id in range(self.population_size)]


class RendezvousState:
    """Pure state machine behind the Ray actor.

    Stable Tune trial IDs receive stable clan ranks. Actor/process instances use fresh
    tokens, allowing paused trials to join a later DDP window without changing their
    logical member identity. Round-result exchange is composed as a separate state
    owner because it synchronizes policy inputs rather than process-group endpoints.
    """

    def __init__(self, population_size: int) -> None:
        if population_size < 2:
            raise ValueError("population_size must be at least 2")
        self.population_size = population_size
        self.member_ranks: dict[str, int] = {}
        self.round_results = RoundResultState(population_size)
        self._pending: dict[str, _PendingMember] = {}
        self._last_tokens: dict[str, str] = {}
        self._current_session: _Session | None = None
        self._next_session_id = 0

    def register_members(self, trial_ids: list[str]) -> None:
        """Assign deterministic ranks after the complete population is known."""

        if len(trial_ids) != self.population_size:
            raise ValueError("Rendezvous requires the complete clan population")
        if len(set(trial_ids)) != len(trial_ids) or any(not item for item in trial_ids):
            raise ValueError("Clan trial IDs must be unique and non-empty")
        member_ranks = {trial_id: rank for rank, trial_id in enumerate(sorted(trial_ids))}
        if self.member_ranks and self.member_ranks != member_ranks:
            raise RuntimeError("Rendezvous was already registered with another population")
        self.member_ranks = member_ranks

    def get_rank(self, trial_id: str) -> int | None:
        return self.member_ranks.get(trial_id)

    def submit_round(self, trial_id: str, record: dict[str, Any]) -> None:
        rank = self._require_rank(trial_id)
        self.round_results.submit(rank, record)

    def get_population(self, trial_id: str, round_index: int) -> list[dict[str, Any]] | None:
        self._require_rank(trial_id)
        return self.round_results.get_population(round_index)

    def announce(
        self,
        trial_id: str,
        token: str,
        host: str,
        port: int | None,
    ) -> None:
        rank = self._require_rank(trial_id)
        if not token:
            raise ValueError("actor token must be non-empty")
        if not host:
            raise ValueError("host must be non-empty")
        if rank == 0 and port is None:
            raise ValueError("Clan rank 0 must publish a rendezvous port")
        if rank != 0 and port is not None:
            raise ValueError("Only clan rank 0 may publish a rendezvous port")
        if self._last_tokens.get(trial_id) == token:
            raise RuntimeError("An actor token cannot be reused for a later clan window")

        self._pending[trial_id] = _PendingMember(token=token, host=host, port=port)
        self._try_create_session()

    def get_session(self, trial_id: str, token: str) -> dict[str, int | str] | None:
        session = self._current_session
        if session is None or session.tokens.get(trial_id) != token:
            return None
        return {
            "session_id": session.session_id,
            "global_rank": self.member_ranks[trial_id],
            "world_size": self.population_size,
            "master_address": session.master_address,
            "master_port": session.master_port,
        }

    def _require_rank(self, trial_id: str) -> int:
        rank = self.member_ranks.get(trial_id)
        if rank is None:
            raise RuntimeError(f"Unknown clan trial {trial_id!r}")
        return rank

    def _try_create_session(self) -> None:
        if len(self.member_ranks) != self.population_size:
            return
        if set(self._pending) != set(self.member_ranks):
            return
        if any(
            self._last_tokens.get(trial_id) == member.token
            for trial_id, member in self._pending.items()
        ):
            return

        rank_zero_trial = next(
            trial_id for trial_id, rank in self.member_ranks.items() if rank == 0
        )
        rank_zero = self._pending[rank_zero_trial]
        assert rank_zero.port is not None
        tokens = {trial_id: member.token for trial_id, member in self._pending.items()}
        self._current_session = _Session(
            session_id=self._next_session_id,
            tokens=tokens,
            master_address=rank_zero.host,
            master_port=rank_zero.port,
        )
        self._next_session_id += 1
        self._last_tokens = tokens
        self._pending = {}


class _RendezvousActor:
    """Thin Ray actor wrapper around deterministic Clan rendezvous state."""

    def __init__(self, population_size: int) -> None:
        self._state = RendezvousState(population_size)

    def validate_population_size(self, population_size: int) -> None:
        if population_size != self._state.population_size:
            raise RuntimeError("Existing rendezvous actor has a different population size")

    def register_members(self, trial_ids: list[str]) -> None:
        self._state.register_members(trial_ids)

    def get_rank(self, trial_id: str) -> int | None:
        return self._state.get_rank(trial_id)

    def submit_round(self, trial_id: str, record: dict[str, Any]) -> None:
        self._state.submit_round(trial_id, record)

    def get_population(self, trial_id: str, round_index: int) -> list[dict[str, Any]] | None:
        return self._state.get_population(trial_id, round_index)

    def announce(
        self,
        trial_id: str,
        token: str,
        host: str,
        port: int | None,
    ) -> None:
        self._state.announce(trial_id, token, host, port)

    def get_session(self, trial_id: str, token: str) -> dict[str, int | str] | None:
        return self._state.get_session(trial_id, token)


def _require_ray():
    try:
        import ray
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Ray Tune support requires the optional dependency: "
            'pip install "clan-based-tuning[ray]"'
        ) from error
    return ray


def get_or_create_rendezvous(clan: _ClanMetadata):
    """Return the named Ray actor for this clan, creating it when necessary."""

    ray = _require_ray()
    remote_actor = ray.remote(_RendezvousActor)
    handle = remote_actor.options(
        name=clan.rendezvous_name,
        namespace=clan.rendezvous_namespace,
        get_if_exists=True,
        num_cpus=0,
    ).remote(clan.population_size)
    ray.get(handle.validate_population_size.remote(clan.population_size))
    return handle


def resolve_tune_runtime(clan: _ClanMetadata) -> _ClanRuntime:
    """Resolve the current native Tune trial into a clan process-group rank."""

    runtime, _ = resolve_tune_membership(clan)
    return runtime


def resolve_tune_membership(clan: _ClanMetadata):
    """Return one trial's process-group runtime and its named rendezvous actor."""

    ray = _require_ray()
    from ray import tune

    trial_id = tune.get_context().get_trial_id()
    if not trial_id:
        raise RuntimeError("Clan integration must run inside a native Ray Tune trial")
    try:
        handle = ray.get_actor(
            clan.rendezvous_name,
            namespace=clan.rendezvous_namespace,
        )
    except ValueError as error:
        raise RuntimeError(
            "Clan rendezvous does not exist. Construct the Tune run with "
            "ClanBasedTraining before resolving the trial session."
        ) from error

    deadline = time.monotonic() + clan.rendezvous_timeout_s
    rank: int | None = None
    while rank is None and time.monotonic() < deadline:
        rank = ray.get(handle.get_rank.remote(trial_id))
        if rank is None:
            time.sleep(clan.rendezvous_poll_interval_s)
    if rank is None:
        raise TimeoutError(f"Trial {trial_id!r} was not registered with the clan scheduler")

    token = uuid4().hex
    host = ray.util.get_node_ip_address()
    port = _find_free_port() if rank == 0 else None
    ray.get(handle.announce.remote(trial_id, token, host, port))

    session: dict[str, int | str] | None = None
    while session is None and time.monotonic() < deadline:
        session = ray.get(handle.get_session.remote(trial_id, token))
        if session is None:
            time.sleep(clan.rendezvous_poll_interval_s)
    if session is None:
        raise TimeoutError(
            "The full clan did not become resident before the rendezvous timeout. "
            "Ensure num_samples and max_concurrent_trials equal population_size "
            "and that the cluster can schedule every member simultaneously."
        )

    runtime = _ClanRuntime(
        trial_id=trial_id,
        actor_token=token,
        session_id=int(session["session_id"]),
        global_rank=int(session["global_rank"]),
        world_size=int(session["world_size"]),
        master_address=str(session["master_address"]),
        master_port=int(session["master_port"]),
        checkpoint_available=tune.get_checkpoint() is not None,
    )
    return runtime, handle


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])
