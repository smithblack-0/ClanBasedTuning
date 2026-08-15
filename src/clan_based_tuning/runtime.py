"""Ray-backed discovery and rendezvous for ordinary Tune function members.

ClanScheduler registers one experiment-scoped trial population in named Ray actors before
members run. ``join_runtime`` uses the current public Tune context to discover that assignment
and rendezvous every independently launched trial into one externally managed Lightning/DDP
world. Pure identity/session behavior lives in ``cohort``; this module owns only Ray actor,
Tune-context, socket, timeout, and process-state effects.
"""

import logging
import socket
import time
from collections.abc import Callable
from typing import Any, NoReturn
from uuid import uuid4

import ray
import torch.distributed as torch_distributed
from ray import tune

from clan_based_tuning.cohort import ClanCoordinator, ClanRuntime, ClanRuntimeSpec, RuntimeRegistry

_RUNTIME_REGISTRY_NAME = "clan-based-tuning-runtime-registry"
_RUNTIME_NAMESPACE = "clan-based-tuning"
_LOGGER = logging.getLogger(__name__)


# Helpers


def _find_free_port() -> int:
    """Return one currently unused local TCP port for the short-lived DDP rendezvous."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("", 0))
        return int(listener.getsockname()[1])


def _distributed_context_is_initialized() -> bool:
    """Return whether this Tune process already owns an initialized PyTorch group."""

    return torch_distributed.is_available() and torch_distributed.is_initialized()


def _wait_for_actor(
    name: str, namespace: str, timeout_s: float, poll_interval_s: float
) -> Any | None:
    """Poll for one named Ray actor until the bounded discovery interval expires."""

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            return ray.get_actor(name, namespace=namespace)
        except ValueError:
            time.sleep(poll_interval_s)
    return None


def _raise_timeout(message: str) -> NoReturn:
    """Log one Clan-owned timeout boundary and raise the corresponding exception."""

    _LOGGER.error("Clan runtime timeout: %s", message)
    raise TimeoutError(message)


# Main


def join_runtime(
    *,
    bootstrap_timeout_s: float = 120.0,
    bootstrap_poll_interval_s: float = 0.05,
    _context_initialized: Callable[[], bool] = _distributed_context_is_initialized,
    _wait_actor: Callable[[str, str, float, float], Any | None] = _wait_for_actor,
    _find_port: Callable[[], int] = _find_free_port,
    _timeout: Callable[[str], NoReturn] = _raise_timeout,
) -> ClanRuntime:
    """Discover and join the Clan assigned to the current ordinary Tune function trial.

    Args:
        bootstrap_timeout_s: Maximum wait for the scheduler registry and this trial's runtime
            assignment before the scheduler-provided cohort timeout is known.
        bootstrap_poll_interval_s: Poll interval used only during that bootstrap phase.
        _context_initialized: Injectable process-state probe for isolated tests.
        _wait_actor: Injectable named-actor discovery operation for isolated tests.
        _find_port: Injectable rank-zero rendezvous-port allocator for isolated tests.
        _timeout: Injectable timeout reporter/raiser for isolated tests.

    Returns:
        Stable member identity plus the rendezvous address/port for Lightning DDP.

    Raises:
        RuntimeError: If called outside Tune or after a previous distributed context remains
            initialized in the reused process.
        TimeoutError: If scheduler registration or complete-cohort rendezvous does not finish.
    """

    if _context_initialized():
        raise RuntimeError(
            "a previous distributed context is still active in this Tune process; "
            "the Clan function path requires a fresh distributed context per resumed generation"
        )

    context = tune.get_context()
    trial_id = context.get_trial_id()
    experiment_name = context.get_experiment_name()
    if not trial_id or not experiment_name:
        raise RuntimeError("ClanDDPStrategy must execute inside a Ray Tune trial")

    registry = _wait_actor(
        _RUNTIME_REGISTRY_NAME,
        _RUNTIME_NAMESPACE,
        bootstrap_timeout_s,
        bootstrap_poll_interval_s,
    )
    if registry is None:
        _timeout("ClanScheduler did not create the runtime registry")

    deadline = time.monotonic() + bootstrap_timeout_s
    runtime_spec = None
    while runtime_spec is None and time.monotonic() < deadline:
        runtime_spec = ray.get(registry.get_runtime_spec.remote(experiment_name, trial_id))
        if runtime_spec is None:
            time.sleep(bootstrap_poll_interval_s)
    if runtime_spec is None:
        _timeout("this Tune trial was not assigned to a complete Clan before its bootstrap timeout")

    coordinator = _wait_actor(
        runtime_spec.coordinator_name,
        runtime_spec.namespace,
        runtime_spec.join_timeout_s,
        runtime_spec.poll_interval_s,
    )
    if coordinator is None:
        _timeout("Clan coordinator was not created by the Tune scheduler")

    deadline = time.monotonic() + runtime_spec.join_timeout_s
    member_id = None
    while member_id is None and time.monotonic() < deadline:
        member_id = ray.get(coordinator.get_member_id.remote(trial_id))
        if member_id is None:
            time.sleep(runtime_spec.poll_interval_s)
    if member_id is None:
        _timeout("the complete Clan was not registered before this trial started")

    token = uuid4().hex
    host = ray.util.get_node_ip_address()
    port = _find_port() if member_id == 0 else None
    ray.get(coordinator.announce.remote(trial_id, token, host, port))

    session = None
    while session is None and time.monotonic() < deadline:
        session = ray.get(coordinator.get_session.remote(trial_id, token))
        if session is None:
            time.sleep(runtime_spec.poll_interval_s)
    if session is None:
        # A timed-out process will not enter DDP. Remove its exact token before raising so a
        # later Tune process cannot form a new session with this dead participant's stale
        # rendezvous address/port.
        ray.get(coordinator.abort_announcement.remote(trial_id, token))
        _timeout(
            "the complete Clan did not become resident before the rendezvous timeout; "
            "provision enough Ray resources to run every member concurrently"
        )

    runtime = ClanRuntime(
        spec=runtime_spec,
        trial_id=trial_id,
        member_id=int(session["member_id"]),
        main_address=str(session["main_address"]),
        main_port=int(session["main_port"]),
    )
    _LOGGER.info(
        "Clan member joined experiment=%s member=%d/%d trial=%s rendezvous=%s:%d",
        runtime.spec.experiment_name,
        runtime.member_id,
        runtime.spec.population_size,
        runtime.trial_id,
        runtime.main_address,
        runtime.main_port,
    )
    return runtime


# Construction


def get_or_create_registry(
    _registry_cls: type[RuntimeRegistry] = RuntimeRegistry,
) -> Any:
    """Construct or reuse the cluster-local actor used to discover Clan assignments.

    Args:
        _registry_cls: Injectable pure registry class used as the Ray actor implementation.

    Returns:
        Ray actor handle for the shared cluster-local runtime registry.
    """

    remote = ray.remote(_registry_cls)
    return remote.options(
        name=_RUNTIME_REGISTRY_NAME,
        namespace=_RUNTIME_NAMESPACE,
        get_if_exists=True,
        num_cpus=0,
    ).remote()


def get_or_create_coordinator(
    runtime_spec: ClanRuntimeSpec,
    _coordinator_cls: type[ClanCoordinator] = ClanCoordinator,
) -> Any:
    """Construct or reuse the named coordinator for one scheduler-owned Clan.

    Args:
        runtime_spec: Immutable cohort identity and population configuration.
        _coordinator_cls: Injectable pure coordinator class used as the Ray actor implementation.

    Returns:
        Ray actor handle whose configured population size matches ``runtime_spec``.
    """

    remote = ray.remote(_coordinator_cls)
    handle = remote.options(
        name=runtime_spec.coordinator_name,
        namespace=runtime_spec.namespace,
        get_if_exists=True,
        num_cpus=0,
    ).remote(runtime_spec.population_size)
    ray.get(handle.validate_population_size.remote(runtime_spec.population_size))
    return handle


def build_runtime_spec(
    *,
    coordinator_name: str,
    experiment_name: str,
    population_size: int,
    metric: str,
    mode: str,
    join_timeout_s: float,
    poll_interval_s: float,
    _cls: type[ClanRuntimeSpec] = ClanRuntimeSpec,
) -> ClanRuntimeSpec:
    """Build the immutable runtime assignment shared by scheduler and member processes.

    Args:
        coordinator_name: Unique Ray actor name for this scheduler instance.
        experiment_name: Tune experiment identity used to scope trial lookup.
        population_size: Complete Clan member count.
        metric: Tune fitness metric name.
        mode: Selection direction, ``"min"`` or ``"max"``.
        join_timeout_s: Bounded complete-cohort rendezvous wait.
        poll_interval_s: Poll cadence while waiting for cohort state.
        _cls: Injectable runtime-spec type for isolated construction tests.

    Returns:
        Immutable runtime assignment in the package-owned Ray namespace.
    """

    return _cls(
        coordinator_name=coordinator_name,
        experiment_name=experiment_name,
        population_size=population_size,
        metric=metric,
        mode=mode,
        join_timeout_s=join_timeout_s,
        poll_interval_s=poll_interval_s,
        namespace=_RUNTIME_NAMESPACE,
    )


def register_runtime_assignment(
    runtime_spec: ClanRuntimeSpec,
    trial_ids: list[str],
    registry_handle: Any | None,
    coordinator_handle: Any | None,
    _get_registry: Callable[[], Any] = get_or_create_registry,
    _get_coordinator: Callable[[ClanRuntimeSpec], Any] = get_or_create_coordinator,
    _resolve: Callable[[Any], Any] = ray.get,
) -> tuple[Any, Any]:
    """Ensure one complete scheduler assignment is live and registered in Ray.

    Args:
        runtime_spec: Immutable assignment shared with every member.
        trial_ids: Complete stable Tune population in member-ID order.
        registry_handle: Previously constructed registry handle, or ``None`` after restore.
        coordinator_handle: Previously constructed coordinator handle, or ``None`` after restore.
        _get_registry: Injectable registry construction function.
        _get_coordinator: Injectable coordinator construction function.
        _resolve: Injectable Ray result resolver used by isolated tests.

    Returns:
        Live ``(registry_handle, coordinator_handle)`` pair for scheduler reuse.
    """

    if registry_handle is None:
        registry_handle = _get_registry()
    if coordinator_handle is None:
        coordinator_handle = _get_coordinator(runtime_spec)

    _resolve(coordinator_handle.register_trials.remote(trial_ids))
    _resolve(
        registry_handle.register_trials.remote(
            runtime_spec.experiment_name,
            trial_ids,
            runtime_spec,
        )
    )
    return registry_handle, coordinator_handle


def release_runtime_assignment(
    runtime_spec: ClanRuntimeSpec,
    trial_ids: list[str],
    registry_handle: Any | None,
    coordinator_handle: Any | None,
    _resolve: Callable[[Any], Any] = ray.get,
    _kill: Callable[..., Any] = ray.kill,
) -> None:
    """Release one successfully completed Clan assignment from long-lived Ray state.

    Args:
        runtime_spec: Assignment whose experiment-scoped trial entries should be removed.
        trial_ids: Complete stable Tune population owned by the scheduler.
        registry_handle: Live shared registry handle, if it still exists.
        coordinator_handle: Live cohort coordinator handle, if it still exists.
        _resolve: Injectable Ray result resolver used by isolated tests.
        _kill: Injectable Ray actor termination operation used by isolated tests.
    """

    if registry_handle is not None:
        _resolve(registry_handle.unregister_trials.remote(runtime_spec.experiment_name, trial_ids))
    if coordinator_handle is not None:
        _kill(coordinator_handle, no_restart=True)
