"""Runtime context joining one Ray Tune function trial to a Clan DDP cohort."""

from __future__ import annotations

import functools
import socket
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ClanRuntimeSpec:
    """Driver-created identity shared by the scheduler and wrapped function trainable."""

    coordinator_name: str
    population_size: int
    metric: str
    mode: str
    controlled_keys: tuple[str, ...]
    join_timeout_s: float
    poll_interval_s: float
    namespace: str = "clan-based-tuning"


@dataclass(frozen=True, slots=True)
class ClanRuntime:
    """Process-local Clan identity and externally assigned DDP topology."""

    spec: ClanRuntimeSpec
    trial_id: str
    member_id: int
    main_address: str
    main_port: int
    genome: dict[str, Any]

    @property
    def world_size(self) -> int:
        return self.spec.population_size

    @property
    def controlled_genome(self) -> dict[str, Any]:
        """Return only the scheduler-controlled values used as producer provenance."""

        return {key: self.genome[key] for key in self.spec.controlled_keys}


@dataclass(frozen=True, slots=True)
class _PendingMember:
    token: str
    host: str
    port: int | None


@dataclass(frozen=True, slots=True)
class _Session:
    session_id: int
    tokens: dict[str, str]
    main_address: str
    main_port: int


class _ClanCoordinator:
    """Hold only stable member assignment and per-invocation rendezvous state."""

    def __init__(self, population_size: int) -> None:
        self.population_size = population_size
        self.member_ids: dict[str, int] = {}
        self._pending: dict[str, _PendingMember] = {}
        self._last_tokens: dict[str, str] = {}
        self._session: _Session | None = None
        self._next_session_id = 0

    def validate_population_size(self, population_size: int) -> None:
        if population_size != self.population_size:
            raise RuntimeError("existing Clan coordinator has a different population size")

    def register_trials(self, trial_ids: list[str]) -> None:
        if len(trial_ids) != self.population_size:
            raise ValueError("Clan coordinator requires the complete Tune population")
        if len(set(trial_ids)) != len(trial_ids):
            raise ValueError("Tune trial IDs must be unique")

        assignment = {trial_id: member_id for member_id, trial_id in enumerate(sorted(trial_ids))}
        if self.member_ids and self.member_ids != assignment:
            raise RuntimeError("Clan coordinator was already registered with another population")
        self.member_ids = assignment

    def get_member_id(self, trial_id: str) -> int | None:
        return self.member_ids.get(trial_id)

    def announce(self, trial_id: str, token: str, host: str, port: int | None) -> None:
        member_id = self._require_member(trial_id)
        if not token:
            raise ValueError("runtime token must be non-empty")
        if not host:
            raise ValueError("runtime host must be non-empty")
        if member_id == 0 and port is None:
            raise ValueError("member zero must provide the DDP rendezvous port")
        if member_id != 0 and port is not None:
            raise ValueError("only member zero may provide the DDP rendezvous port")
        if self._last_tokens.get(trial_id) == token:
            raise RuntimeError("a function invocation cannot reuse its previous runtime token")

        self._pending[trial_id] = _PendingMember(token=token, host=host, port=port)
        self._try_open_session()

    def get_session(self, trial_id: str, token: str) -> dict[str, int | str] | None:
        session = self._session
        if session is None or session.tokens.get(trial_id) != token:
            return None
        return {
            "session_id": session.session_id,
            "member_id": self.member_ids[trial_id],
            "main_address": session.main_address,
            "main_port": session.main_port,
        }

    def _require_member(self, trial_id: str) -> int:
        member_id = self.member_ids.get(trial_id)
        if member_id is None:
            raise RuntimeError(f"Tune trial {trial_id!r} is not registered with this Clan")
        return member_id

    def _try_open_session(self) -> None:
        if len(self.member_ids) != self.population_size:
            return
        if set(self._pending) != set(self.member_ids):
            return

        rank_zero_trial = next(
            trial_id for trial_id, member_id in self.member_ids.items() if member_id == 0
        )
        rank_zero = self._pending[rank_zero_trial]
        assert rank_zero.port is not None

        tokens = {trial_id: member.token for trial_id, member in self._pending.items()}
        self._session = _Session(
            session_id=self._next_session_id,
            tokens=tokens,
            main_address=rank_zero.host,
            main_port=rank_zero.port,
        )
        self._next_session_id += 1
        self._last_tokens = tokens
        self._pending = {}


_CURRENT_RUNTIME: ContextVar[ClanRuntime | None] = ContextVar(
    "clan_based_tuning_runtime", default=None
)


def current_runtime() -> ClanRuntime:
    """Return the active Clan runtime for the current wrapped Tune function."""

    runtime = _CURRENT_RUNTIME.get()
    if runtime is None:
        raise RuntimeError(
            "no active Clan runtime; pass the Tune function through ClanScheduler.wrap()"
        )
    return runtime


def wrap_function_trainable(
    trainable: Callable[[dict[str, Any]], Any],
    runtime_spec: ClanRuntimeSpec,
) -> Callable[[dict[str, Any]], Any]:
    """Wrap a Ray function trainable without changing the genome it receives."""

    @functools.wraps(trainable)
    def wrapped(genome: dict[str, Any]):
        runtime = _join_runtime(runtime_spec, genome)
        token = _CURRENT_RUNTIME.set(runtime)
        try:
            return trainable(genome)
        finally:
            _CURRENT_RUNTIME.reset(token)

    return wrapped


def get_or_create_coordinator(runtime_spec: ClanRuntimeSpec):
    """Return the named Ray coordinator owned by the Tune scheduler."""

    import ray

    remote = ray.remote(_ClanCoordinator)
    handle = remote.options(
        name=runtime_spec.coordinator_name,
        namespace=runtime_spec.namespace,
        get_if_exists=True,
        num_cpus=0,
    ).remote(runtime_spec.population_size)
    ray.get(handle.validate_population_size.remote(runtime_spec.population_size))
    return handle


def _join_runtime(runtime_spec: ClanRuntimeSpec, genome: dict[str, Any]) -> ClanRuntime:
    import ray
    from ray import tune

    if _torch_distributed_is_initialized():
        raise RuntimeError(
            "a previous distributed context is still active in this Tune process; "
            "the initial Clan function path requires a fresh process per resumed generation"
        )

    trial_id = tune.get_context().get_trial_id()
    if not trial_id:
        raise RuntimeError("ClanScheduler.wrap() must execute inside a Ray Tune trial")

    deadline = time.monotonic() + runtime_spec.join_timeout_s
    handle = None
    while handle is None and time.monotonic() < deadline:
        try:
            handle = ray.get_actor(runtime_spec.coordinator_name, namespace=runtime_spec.namespace)
        except ValueError:
            time.sleep(runtime_spec.poll_interval_s)
    if handle is None:
        raise TimeoutError("Clan coordinator was not created by the Tune scheduler")

    member_id = None
    while member_id is None and time.monotonic() < deadline:
        member_id = ray.get(handle.get_member_id.remote(trial_id))
        if member_id is None:
            time.sleep(runtime_spec.poll_interval_s)
    if member_id is None:
        raise TimeoutError(
            "the complete Clan was not registered before this Tune trial attempted to start"
        )

    token = uuid4().hex
    host = ray.util.get_node_ip_address()
    port = _find_free_port() if member_id == 0 else None
    ray.get(handle.announce.remote(trial_id, token, host, port))

    session = None
    while session is None and time.monotonic() < deadline:
        session = ray.get(handle.get_session.remote(trial_id, token))
        if session is None:
            time.sleep(runtime_spec.poll_interval_s)
    if session is None:
        raise TimeoutError(
            "the complete Clan did not become resident before the rendezvous timeout; "
            "the initial path requires enough resources to run every member concurrently"
        )

    return ClanRuntime(
        spec=runtime_spec,
        trial_id=trial_id,
        member_id=int(session["member_id"]),
        main_address=str(session["main_address"]),
        main_port=int(session["main_port"]),
        genome=dict(genome),
    )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("", 0))
        return int(listener.getsockname()[1])


def _torch_distributed_is_initialized() -> bool:
    try:
        import torch.distributed
    except ModuleNotFoundError:
        return False
    return torch.distributed.is_available() and torch.distributed.is_initialized()
