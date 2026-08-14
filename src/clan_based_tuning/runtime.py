"""Ray-backed discovery and rendezvous for ordinary Tune function members.

ClanScheduler registers one experiment-scoped trial population in named Ray actors before
members run. ``join_runtime`` uses the current public Tune context to discover that assignment
and rendezvous every independently launched trial into one externally managed Lightning/DDP
world. Pure identity/session behavior lives in ``cohort``; this module owns only Ray actor,
Tune-context, socket, timeout, and process-state effects.
"""

import socket
import time
from typing import Any
from uuid import uuid4

import ray
import torch.distributed as torch_distributed
from ray import tune

from clan_based_tuning.cohort import ClanCoordinator, ClanRuntime, ClanRuntimeSpec, RuntimeRegistry

_RUNTIME_REGISTRY_NAME = "clan-based-tuning-runtime-registry"
_RUNTIME_NAMESPACE = "clan-based-tuning"


# Helpers


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("", 0))
        return int(listener.getsockname()[1])


def _distributed_context_is_initialized() -> bool:
    return torch_distributed.is_available() and torch_distributed.is_initialized()


def _wait_for_actor(
    name: str, namespace: str, timeout_s: float, poll_interval_s: float
) -> Any | None:
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
) -> ClanRuntime:
    """Discover and join the Clan assigned to the current ordinary Tune function trial.

    Args:
        bootstrap_timeout_s: Maximum wait for the scheduler registry and this trial's runtime
            assignment before the scheduler-provided cohort timeout is known.
        bootstrap_poll_interval_s: Poll interval used only during that bootstrap phase.

    Returns:
        Stable member identity plus the rendezvous address/port for Lightning DDP.

    Raises:
        RuntimeError: If called outside Tune or after a previous distributed context remains
            initialized in the reused process.
        TimeoutError: If scheduler registration or complete-cohort rendezvous does not finish.
    """

    if _distributed_context_is_initialized():
        raise RuntimeError(
            "a previous distributed context is still active in this Tune process; "
            "the Clan function path requires a fresh distributed context per resumed generation"
        )

    context = tune.get_context()
    trial_id = context.get_trial_id()
    experiment_name = context.get_experiment_name()
    if not trial_id or not experiment_name:
        raise RuntimeError("ClanDDPStrategy must execute inside a Ray Tune trial")

    registry = _wait_for_actor(
        _RUNTIME_REGISTRY_NAME,
        _RUNTIME_NAMESPACE,
        bootstrap_timeout_s,
        bootstrap_poll_interval_s,
    )
    if registry is None:
        raise TimeoutError("ClanScheduler did not create the runtime registry")

    deadline = time.monotonic() + bootstrap_timeout_s
    runtime_spec = None
    while runtime_spec is None and time.monotonic() < deadline:
        runtime_spec = ray.get(registry.get_runtime_spec.remote(experiment_name, trial_id))
        if runtime_spec is None:
            time.sleep(bootstrap_poll_interval_s)
    if runtime_spec is None:
        raise TimeoutError(
            "this Tune trial was not assigned to a complete Clan before its bootstrap timeout"
        )

    coordinator = _wait_for_actor(
        runtime_spec.coordinator_name,
        runtime_spec.namespace,
        runtime_spec.join_timeout_s,
        runtime_spec.poll_interval_s,
    )
    if coordinator is None:
        raise TimeoutError("Clan coordinator was not created by the Tune scheduler")

    deadline = time.monotonic() + runtime_spec.join_timeout_s
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
            "provision enough Ray resources to run every member concurrently"
        )

    return ClanRuntime(
        spec=runtime_spec,
        trial_id=trial_id,
        member_id=int(session["member_id"]),
        main_address=str(session["main_address"]),
        main_port=int(session["main_port"]),
    )


# Construction


def get_or_create_registry(
    _registry_cls: type[RuntimeRegistry] = RuntimeRegistry,
) -> Any:
    """Return the cluster-local named actor used to discover Clan assignments."""

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
    """Return the named cohort coordinator owned by one Clan scheduler instance."""

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
    """Build one immutable runtime assignment shared by scheduler and members."""

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
