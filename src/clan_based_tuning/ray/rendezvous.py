"""Ray rendezvous for native Tune trials joining one DDP process group."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from uuid import uuid4

from clan_based_tuning.lightning.environment import ClanRuntime
from clan_based_tuning.spec import ClanSpec


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


class RendezvousState:
    """Pure state machine behind the Ray actor.

    Stable Tune trial IDs receive stable clan ranks. Actor/process instances use
    fresh tokens, allowing paused or failed trials to rejoin a later window
    without changing their logical trial identity.
    """

    def __init__(self, population_size: int) -> None:
        if population_size < 2:
            raise ValueError("population_size must be at least 2")
        self.population_size = population_size
        self.member_ranks: dict[str, int] = {}
        self._pending: dict[str, _PendingMember] = {}
        self._last_tokens: dict[str, str] = {}
        self._current_session: _Session | None = None
        self._next_session_id = 0

    def register_member(self, trial_id: str, rank: int) -> None:
        if not trial_id:
            raise ValueError("trial_id must be non-empty")
        if not 0 <= rank < self.population_size:
            raise ValueError("rank must be within population_size")
        previous_rank = self.member_ranks.get(trial_id)
        if previous_rank is not None and previous_rank != rank:
            raise RuntimeError(
                f"Trial {trial_id!r} was already registered as rank {previous_rank}"
            )
        other_trial = next(
            (
                other_id
                for other_id, other_rank in self.member_ranks.items()
                if other_rank == rank and other_id != trial_id
            ),
            None,
        )
        if other_trial is not None:
            raise RuntimeError(
                f"Clan rank {rank} is already assigned to trial {other_trial!r}"
            )
        self.member_ranks[trial_id] = rank

    def register_members(self, member_ranks: dict[str, int]) -> None:
        for trial_id, rank in member_ranks.items():
            self.register_member(trial_id, rank)

    def get_rank(self, trial_id: str) -> int | None:
        return self.member_ranks.get(trial_id)

    def announce(
        self,
        trial_id: str,
        token: str,
        host: str,
        port: int | None,
    ) -> None:
        rank = self.member_ranks.get(trial_id)
        if rank is None:
            raise RuntimeError(f"Unknown clan trial {trial_id!r}")
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
        tokens = {
            trial_id: member.token for trial_id, member in self._pending.items()
        }
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
    """Thin Ray actor wrapper around the deterministic rendezvous state."""

    def __init__(self, population_size: int) -> None:
        self._state = RendezvousState(population_size)

    def validate_population_size(self, population_size: int) -> None:
        if population_size != self._state.population_size:
            raise RuntimeError(
                "Existing rendezvous actor has a different population size"
            )

    def register_members(self, member_ranks: dict[str, int]) -> None:
        self._state.register_members(member_ranks)

    def get_rank(self, trial_id: str) -> int | None:
        return self._state.get_rank(trial_id)

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


def get_or_create_rendezvous(clan: ClanSpec):
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


def resolve_tune_runtime(clan: ClanSpec) -> ClanRuntime:
    """Resolve the current native Tune trial into a clan process-group rank."""

    ray = _require_ray()
    from ray import tune

    trial_id = tune.get_context().get_trial_id()
    if not trial_id:
        raise RuntimeError("ClanDDPStrategy must run inside a native Ray Tune trial")
    try:
        handle = ray.get_actor(
            clan.rendezvous_name,
            namespace=clan.rendezvous_namespace,
        )
    except ValueError as error:
        raise RuntimeError(
            "Clan rendezvous does not exist. Construct the Tune run with "
            "ClanBasedTraining before creating ClanDDPStrategy."
        ) from error

    deadline = time.monotonic() + clan.rendezvous_timeout_s
    rank: int | None = None
    while rank is None and time.monotonic() < deadline:
        rank = ray.get(handle.get_rank.remote(trial_id))
        if rank is None:
            time.sleep(clan.rendezvous_poll_interval_s)
    if rank is None:
        raise TimeoutError(
            f"Trial {trial_id!r} was not registered with the clan scheduler"
        )

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

    return ClanRuntime(
        trial_id=trial_id,
        actor_token=token,
        session_id=int(session["session_id"]),
        global_rank=int(session["global_rank"]),
        world_size=int(session["world_size"]),
        master_address=str(session["master_address"]),
        master_port=int(session["master_port"]),
        checkpoint_available=tune.get_checkpoint() is not None,
    )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])
