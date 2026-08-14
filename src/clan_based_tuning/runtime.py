"""Runtime rendezvous joining Ray Tune trials to one Clan DDP cohort."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass

_RUNTIME_REGISTRY_NAME = "clan-based-tuning-runtime-registry"
_RUNTIME_NAMESPACE = "clan-based-tuning"


@dataclass(frozen=True, slots=True)
class ClanRuntimeSpec:
    """Scheduler-owned identity and configuration required by one Clan cohort."""

    coordinator_name: str
    population_size: int
    metric: str
    mode: str
    join_timeout_s: float
    poll_interval_s: float
    namespace: str = _RUNTIME_NAMESPACE


@dataclass(frozen=True, slots=True)
class ClanRuntime:
    """Process-local stable member identity and externally assigned DDP topology."""

    spec: ClanRuntimeSpec
    trial_id: str
    member_id: int
    main_address: str
    main_port: int

    @property
    def world_size(self) -> int:
        return self.spec.population_size


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


class _RuntimeRegistry:
    """Map Tune trial IDs to scheduler-owned Clan runtime specifications."""

    def __init__(self) -> None:
        self._runtime_specs: dict[str, ClanRuntimeSpec] = {}

    def register_trials(self, trial_ids: list[str], runtime_spec: ClanRuntimeSpec) -> None:
        for trial_id in trial_ids:
            existing = self._runtime_specs.get(trial_id)
            if existing is not None and existing != runtime_spec:
                raise RuntimeError(
                    f"Tune trial {trial_id!r} is already registered with another Clan runtime"
                )
        for trial_id in trial_ids:
            self._runtime_specs[trial_id] = runtime_spec

    def get_runtime_spec(self, trial_id: str) -> ClanRuntimeSpec | None:
        return self._runtime_specs.get(trial_id)


class _ClanCoordinator:
    """Hold stable member assignment and per-invocation rendezvous state only."""

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


def get_or_create_registry():
    """Return the cluster-local registry used to discover Clan runtime assignments."""

    import ray

    remote = ray.remote(_RuntimeRegistry)
    return remote.options(
        name=_RUNTIME_REGISTRY_NAME,
        namespace=_RUNTIME_NAMESPACE,
        get_if_exists=True,
        num_cpus=0,
    ).remote()


def get_or_create_coordinator(runtime_spec: ClanRuntimeSpec):
    """Return the named cohort coordinator owned by the Tune scheduler."""

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


def join_runtime() -> ClanRuntime:
    """Discover and join the Clan assigned to the current ordinary Tune function trial."""

    from uuid import uuid4

    import ray
    from ray import tune

    if _torch_distributed_is_initialized():
        raise RuntimeError(
            "a previous distributed context is still active in this Tune process; "
            "the initial Clan function path requires a fresh process per resumed generation"
        )

    trial_id = tune.get_context().get_trial_id()
    if not trial_id:
        raise RuntimeError("ClanDDPStrategy must execute inside a Ray Tune trial")

    registry = None
    deadline = time.monotonic() + 120.0
    while registry is None and time.monotonic() < deadline:
        try:
            registry = ray.get_actor(_RUNTIME_REGISTRY_NAME, namespace=_RUNTIME_NAMESPACE)
        except ValueError:
            time.sleep(0.05)
    if registry is None:
        raise TimeoutError("ClanScheduler did not create the runtime registry")

    runtime_spec = None
    while runtime_spec is None and time.monotonic() < deadline:
        runtime_spec = ray.get(registry.get_runtime_spec.remote(trial_id))
        if runtime_spec is None:
            time.sleep(0.05)
    if runtime_spec is None:
        raise TimeoutError(
            "this Tune trial was not assigned to a complete Clan before its rendezvous timeout"
        )

    deadline = time.monotonic() + runtime_spec.join_timeout_s
    coordinator = None
    while coordinator is None and time.monotonic() < deadline:
        try:
            coordinator = ray.get_actor(
                runtime_spec.coordinator_name,
                namespace=runtime_spec.namespace,
            )
        except ValueError:
            time.sleep(runtime_spec.poll_interval_s)
    if coordinator is None:
        raise TimeoutError("Clan coordinator was not created by the Tune scheduler")

    member_id = None
    while member_id is None and time.monotonic() < deadline:
        member_id = ray.get(coordinator.get_member_id.remote(trial_id))
        if member_id is None:
            time.sleep(runtime_spec.poll_interval_s)
    if member_id is None:
        raise TimeoutError("the complete Clan was not registered before this trial started")

    token = uuid4().hex
    host = ray.util.get_node_ip_address()
    port = _find_free_port() if member_id == 0 else None
    ray.get(coordinator.announce.remote(trial_id, token, host, port))

    session = None
    while session is None and time.monotonic() < deadline:
        session = ray.get(coordinator.get_session.remote(trial_id, token))
        if session is None:
            time.sleep(runtime_spec.poll_interval_s)
    if session is None:
        raise TimeoutError(
            "the complete Clan did not become resident before the rendezvous timeout; "
            "provide enough Ray resources to run every member concurrently"
        )

    return ClanRuntime(
        spec=runtime_spec,
        trial_id=trial_id,
        member_id=int(session["member_id"]),
        main_address=str(session["main_address"]),
        main_port=int(session["main_port"]),
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
