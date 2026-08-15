"""Unit contracts for Ray runtime publication and successful-run cleanup.

The production functions are small effect boundaries whose ordering matters: coordinator state
must exist before registry publication, and registry discovery must disappear before the
coordinator is killed. These tests replace only Ray handles/resolution so that ordering and
ownership can be asserted without making the unit suite depend on a live Ray runtime.
"""

from typing import Any

from clan_based_tuning.cohort import ClanRuntimeSpec
from clan_based_tuning.runtime import register_runtime_assignment, release_runtime_assignment


class FakeRemoteMethod:
    """Mimic Ray's ``actor.method.remote(...)`` shape while retaining call order/input evidence."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[Any, ...]] = []

    def remote(self, *args: Any) -> tuple[str, tuple[Any, ...]]:
        """Produce a resolver-visible sentinel so tests can prove each remote write was awaited."""

        self.calls.append(args)
        return self.name, args


class FakeActor:
    """Expose only the two RPCs used by the runtime publication/cleanup contract."""

    def __init__(self) -> None:
        self.register_trials = FakeRemoteMethod("register")
        self.unregister_trials = FakeRemoteMethod("unregister")


def _runtime_spec() -> ClanRuntimeSpec:
    """Keep one canonical assignment so construction and publication assertions cannot drift."""

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
    """Publish the registry entry only after the complete coordinator assignment resolves."""

    registry = FakeActor()
    coordinator = FakeActor()
    resolved: list[Any] = []

    def get_registry() -> FakeActor:
        """Stand in for cluster-wide registry construction without starting Ray."""

        return registry

    def get_coordinator(runtime_spec: ClanRuntimeSpec) -> FakeActor:
        """Ensure coordinator construction receives the exact immutable assignment under test."""

        assert runtime_spec == _runtime_spec()
        return coordinator

    def resolve(value: Any) -> Any:
        """Record synchronous completion so publication ordering is observable."""

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
    assert resolved == [
        ("register", (["trial-a", "trial-b"],)),
        ("register", ("experiment-a", ["trial-a", "trial-b"], _runtime_spec())),
    ]


def test_release_unregisters_trials_and_kills_only_coordinator() -> None:
    """Withdraw shared discovery state before terminating only the cohort-owned actor."""

    registry = FakeActor()
    coordinator = FakeActor()
    resolved: list[Any] = []
    killed: list[tuple[Any, bool]] = []

    def resolve(value: Any) -> Any:
        """Make completion of the registry withdrawal visible before actor termination."""

        resolved.append(value)
        return value

    def kill(actor: Any, *, no_restart: bool) -> None:
        """Capture the actor selected for destruction without touching the shared registry."""

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
    assert resolved == [("unregister", ("experiment-a", ["trial-a", "trial-b"]))]
    assert killed == [(coordinator, True)]
