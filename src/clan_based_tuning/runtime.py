"""Ray-backed discovery and rendezvous for ordinary Tune function members.

``ClanScheduler`` publishes one experiment-scoped population assignment before Tune workers
run. ``join_runtime`` then lets each independently launched function process discover that
assignment and rendezvous with the other members before Lightning initializes DDP. Pure
identity/session rules live in ``cohort``; this module owns the effects required to make those
rules work in Ray: named actors, Tune context, sockets, polling, logging, and actor lifecycle.

Discovery and cohort rendezvous intentionally use different timeout phases. Bootstrap timeout
covers "can this worker find scheduler authority at all?"; the scheduler-provided join timeout
covers "can the complete already-defined Clan become resident together?". Keeping those
failures distinct makes insufficient cluster capacity diagnosable rather than looking like a
missing scheduler.
"""

import logging
import socket
import time
from collections.abc import Callable
from typing import Any
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
    """Choose the rank-zero rendezvous port without pretending to reserve it.

    The temporary socket is closed before PyTorch later binds the process group, so this is a
    best-effort free-port selection rather than an atomic reservation. It is kept behind one
    effect seam because only rank zero should touch local socket allocation and tests should
    not need a real listener.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("", 0))
        return int(listener.getsockname()[1])


def _distributed_context_is_initialized() -> bool:
    """Probe process-global DDP state that may survive a reused Ray worker process.

    CBT expects each resumed function invocation to construct a fresh Lightning/PyTorch
    process group. Entering with an existing group risks silently joining the new generation
    to stale distributed state, so ``join_runtime`` fails before discovery when this is true.
    """

    return torch_distributed.is_available() and torch_distributed.is_initialized()


def _wait_for_actor(
    name: str, namespace: str, timeout_s: float, poll_interval_s: float
) -> Any | None:
    """Bound the race between worker startup and creation of one scheduler-owned named actor.

    Ray reports a missing named actor as ``ValueError``. Other actor/API failures are allowed
    to propagate because treating them as "not created yet" would hide a real runtime defect.
    """

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            return ray.get_actor(name, namespace=namespace)
        except ValueError:
            time.sleep(poll_interval_s)
    return None


# Main


def join_runtime(
    *,
    bootstrap_timeout_s: float = 120.0,
    bootstrap_poll_interval_s: float = 0.05,
    _context_initialized: Callable[[], bool] = _distributed_context_is_initialized,
    _wait_actor: Callable[[str, str, float, float], Any | None] = _wait_for_actor,
    _find_port: Callable[[], int] = _find_free_port,
) -> ClanRuntime:
    """Resolve this Tune invocation into one stable Clan rank and DDP rendezvous.

    The sequence is deliberate. First discover the cluster-wide registry using only public Tune
    context. Then poll for this experiment/trial's immutable runtime spec. Only after that spec
    exists do we know the cohort-specific timeout and coordinator name. Finally announce a
    fresh invocation token and wait for a session containing that exact token.

    Member-ID lookup and session formation share one join deadline. This bounds the complete
    cohort admission phase rather than accidentally granting a full timeout to each sub-step.
    If session formation times out, the process retracts its exact announcement before raising
    so a later retry cannot rendezvous with this dead process's address/port.

    Args:
        bootstrap_timeout_s: Maximum wait for scheduler discovery before cohort-specific facts
            are available.
        bootstrap_poll_interval_s: Poll cadence during only that bootstrap discovery phase.
        _context_initialized: Process-global DDP-state probe; replacements must detect stale
            groups before a new invocation joins.
        _wait_actor: Named-actor lookup seam; replacements must distinguish absence from other
            Ray failures.
        _find_port: Rank-zero socket-allocation seam used before process-group initialization.

    Raises:
        RuntimeError: If called outside Tune or with a stale distributed process group.
        TimeoutError: At a logged CBT-owned bootstrap or complete-cohort admission boundary.
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
        message = "ClanScheduler did not create the runtime registry"
        _LOGGER.error("Clan runtime timeout: %s", message)
        raise TimeoutError(message)

    deadline = time.monotonic() + bootstrap_timeout_s
    runtime_spec = None
    while runtime_spec is None and time.monotonic() < deadline:
        runtime_spec = ray.get(registry.get_runtime_spec.remote(experiment_name, trial_id))
        if runtime_spec is None:
            time.sleep(bootstrap_poll_interval_s)
    if runtime_spec is None:
        message = "this Tune trial was not assigned to a complete Clan before its bootstrap timeout"
        _LOGGER.error("Clan runtime timeout: %s", message)
        raise TimeoutError(message)

    coordinator = _wait_actor(
        runtime_spec.coordinator_name,
        runtime_spec.namespace,
        runtime_spec.join_timeout_s,
        runtime_spec.poll_interval_s,
    )
    if coordinator is None:
        message = "Clan coordinator was not created by the Tune scheduler"
        _LOGGER.error("Clan runtime timeout: %s", message)
        raise TimeoutError(message)

    deadline = time.monotonic() + runtime_spec.join_timeout_s
    member_id = None
    while member_id is None and time.monotonic() < deadline:
        member_id = ray.get(coordinator.get_member_id.remote(trial_id))
        if member_id is None:
            time.sleep(runtime_spec.poll_interval_s)
    if member_id is None:
        message = "the complete Clan was not registered before this trial started"
        _LOGGER.error("Clan runtime timeout: %s", message)
        raise TimeoutError(message)

    token = uuid4().hex
    main_address = ray.util.get_node_ip_address() if member_id == 0 else None
    main_port = _find_port() if member_id == 0 else None
    ray.get(coordinator.announce.remote(trial_id, token, main_address, main_port))

    session = None
    while session is None and time.monotonic() < deadline:
        session = ray.get(coordinator.get_session.remote(trial_id, token))
        if session is None:
            time.sleep(runtime_spec.poll_interval_s)
    if session is None:
        ray.get(coordinator.abort_announcement.remote(trial_id, token))
        message = (
            "the complete Clan did not become resident before the rendezvous timeout; "
            "provision enough Ray resources to run every member concurrently"
        )
        _LOGGER.error("Clan runtime timeout: %s", message)
        raise TimeoutError(message)

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
    """Return the cluster-wide discovery actor shared by independent Clan experiments.

    The fixed name/namespace is intentional: workers know neither scheduler object identity nor
    actor handles when Tune starts them, so they need one stable rendezvous for discovering
    experiment-scoped assignments. ``get_if_exists`` makes scheduler restore idempotent.
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
    """Return this scheduler instance's cohort actor, validating safe named-actor reuse.

    Restore may find an actor with the same scheduler-owned name. Population size is checked
    immediately because reusing an actor with a different immutable cohort shape would remap
    ranks before any worker had a chance to detect the conflict.
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
    """Keep runtime namespace and immutable worker-discovery facts out of scheduler policy.

    This construction boundary looks small but owns an important dependency direction: the
    scheduler supplies algorithm/runtime values without importing the private Ray actor
    namespace contract. A replacement spec type must preserve those immutable discovery facts.
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
    """Make a complete cohort discoverable without exposing half-registered state to workers.

    The coordinator receives the complete trial population first. Only after that write has
    resolved is the experiment/trial mapping published in the shared registry. A worker that
    discovers the registry entry can therefore safely proceed to the coordinator instead of
    racing an uninitialized member assignment. Existing handles are reused during ordinary
    callbacks; ``None`` handles reconstruct actors after scheduler deserialization.
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
    """Withdraw successful-run discovery before terminating the cohort-specific actor.

    Removal order is the inverse of publication: first delete this experiment's registry keys
    so no new worker can discover a coordinator that is about to disappear, then kill only the
    scheduler-owned coordinator. The shared registry remains alive for unrelated experiments.
    Error paths deliberately retain state for Ray retry/restore rather than calling this
    successful-completion cleanup.
    """

    if registry_handle is not None:
        _resolve(registry_handle.unregister_trials.remote(runtime_spec.experiment_name, trial_ids))
    if coordinator_handle is not None:
        _kill(coordinator_handle, no_restart=True)
