"""Unit contracts for Ray runtime construction and release boundaries.

These tests avoid real actors by injecting tiny handles into the runtime construction
functions. They prove that actor construction stays outside ``ClanScheduler``, existing
handles are reusable, registration is resolved before use, and successful completion removes
registry assignments and terminates only the scheduler-owned coordinator.
"""

from typing import Any

from clan_based_tuning.cohort import ClanRuntimeSpec
from clan_based_tuning.runtime import register_runtime_assignment, release_runtime_assignment


class FakeRemoteMethod:
    """Record actor-method invocations while returning a resolvable sentinel."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[Any, ...]] = []

    def remote(self, *args: Any) -> tuple[str, tuple[Any, ...]]:
        """Record one remote call and return a stable value for the injected resolver."""

        self.calls.append(args)
        return self.name, args


class FakeActor:
    """Expose only the actor methods used by runtime registration and release."""

    def __init__(self) -> None:
        self.register_trials = FakeRemoteMethod("register")
        self.unregister_trials = FakeRemoteMethod("unregister")


def _runtime_spec() -> ClanRuntimeSpec:
    """Build one immutable assignment for runtime-construction unit contracts."""

    return ClanRuntimeSpec(
        coordinator_name="coordinator-a",
        experiment_name="experiment-a",
        population_size=2,
        metric="val_loss",
        mode="min",
        join_timeout_s=60.0,
        poll_interval_s=0.05,
        namespace="clan-based-tuning",
    )


def test_registration_constructs_missing_handles_and_registers_complete_assignment() -> None:
    """Construction functions are invoked only for missing handles and both writes resolve."""

    registry = FakeActor()
    coordinator = FakeActor()
    resolved: list[Any] = []

    def get_registry() -> FakeActor:
        """Return the injected registry handle."""

        return registry

    def get_coordinator(runtime_spec: ClanRuntimeSpec) -> FakeActor:
        """Return the injected coordinator after checking the requested assignment."""

        assert runtime_spec == _runtime_spec()
        return coordinator

    def resolve(value: Any) -> Any:
        """Record each synchronously resolved actor operation."""

        resolved.append(value)
        return value

    handles = register_runtime_assignment(
        _runtime_spec(),
        ["trial-a", "trial-b"],
        None,
        None,
        _get_registry=get_registry,
        _get_coordinator=get_coordinator,
        _resolve=resolve,
    )

    assert handles == (registry, coordinator)
    assert coordinator.register_trials.calls == [(["trial-a", "trial-b"],)]
    assert registry.register_trials.calls == [
        ("experiment-a", ["trial-a", "trial-b"], _runtime_spec())
    ]
    assert len(resolved) == 2


def test_release_unregisters_trials_and_kills_only_coordinator() -> None:
    """Successful completion clears the shared registry before terminating its cohort actor."""

    registry = FakeActor()
    coordinator = FakeActor()
    resolved: list[Any] = []
    killed: list[tuple[Any, bool]] = []

    def resolve(value: Any) -> Any:
        """Record the registry mutation completion."""

        resolved.append(value)
        return value

    def kill(actor: Any, *, no_restart: bool) -> None:
        """Record the scheduler-owned actor selected for termination."""

        killed.append((actor, no_restart))

    release_runtime_assignment(
        _runtime_spec(),
        ["trial-a", "trial-b"],
        registry,
        coordinator,
        _resolve=resolve,
        _kill=kill,
    )

    assert registry.unregister_trials.calls == [("experiment-a", ["trial-a", "trial-b"])]
    assert len(resolved) == 1
    assert killed == [(coordinator, True)]
