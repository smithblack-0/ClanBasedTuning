"""Pure-state contracts for experiment identity, stable ranks, and invocation rendezvous.

These tests deliberately exclude Ray so failures identify the cohort state machine rather than
actor/runtime behavior. They pin the properties distributed integration depends on: experiment
scoping, deterministic member assignment, complete same-invocation session formation, and
compare-before-delete cleanup of timed-out announcements.
"""

import pytest

from clan_based_tuning.cohort import ClanCoordinator, ClanRuntimeSpec, RuntimeRegistry


def _runtime_spec(
    coordinator_name: str = "coordinator-a",
    experiment_name: str = "experiment-a",
) -> ClanRuntimeSpec:
    """Centralize immutable assignment values so identity-scoping tests vary only identity."""

    return ClanRuntimeSpec(
        coordinator_name=coordinator_name,
        experiment_name=experiment_name,
        population_size=2,
        metric="val_loss",
        mode="min",
        join_timeout_s=60.0,
        poll_interval_s=0.05,
        namespace="clan-based-tuning",
    )


def test_registry_scopes_trial_ids_by_experiment_rejects_conflicts_and_releases() -> None:
    """The same Tune trial ID may exist in two experiments but never map twice within one."""

    registry = RuntimeRegistry()
    first = _runtime_spec()
    second_experiment = _runtime_spec("coordinator-b", "experiment-b")

    registry.register_trials("experiment-a", ["trial-b", "trial-a"], first)
    registry.register_trials("experiment-a", ["trial-b", "trial-a"], first)
    registry.register_trials("experiment-b", ["trial-a"], second_experiment)

    assert registry.get_runtime_spec("experiment-a", "trial-a") == first
    assert registry.get_runtime_spec("experiment-b", "trial-a") == second_experiment

    with pytest.raises(RuntimeError, match="another Clan runtime"):
        registry.register_trials(
            "experiment-a",
            ["trial-a"],
            _runtime_spec("coordinator-c", "experiment-a"),
        )

    registry.unregister_trials("experiment-a", ["trial-a", "trial-b"])
    assert registry.get_runtime_spec("experiment-a", "trial-a") is None
    assert registry.get_runtime_spec("experiment-a", "trial-b") is None
    assert registry.get_runtime_spec("experiment-b", "trial-a") == second_experiment


def test_coordinator_assigns_stable_members_and_opens_only_complete_sessions() -> None:
    """Sorted trial identity fixes rank order and no member sees a session before the cohort."""

    coordinator = ClanCoordinator(population_size=2)
    coordinator.register_trials(["trial-b", "trial-a"])

    assert coordinator.get_member_id("trial-a") == 0
    assert coordinator.get_member_id("trial-b") == 1

    coordinator.announce("trial-a", "token-a", "host-a", 12345)
    assert coordinator.get_session("trial-a", "token-a") is None

    coordinator.announce("trial-b", "token-b", "host-b", None)
    assert coordinator.get_session("trial-a", "token-a") == {
        "session_id": 0,
        "member_id": 0,
        "main_address": "host-a",
        "main_port": 12345,
    }
    assert coordinator.get_session("trial-b", "token-b") == {
        "session_id": 0,
        "member_id": 1,
        "main_address": "host-a",
        "main_port": 12345,
    }


def test_aborted_announcement_cannot_form_a_session_with_a_later_member() -> None:
    """Timeout cleanup removes dead peers without allowing an older process to erase a retry."""

    coordinator = ClanCoordinator(population_size=2)
    coordinator.register_trials(["trial-a", "trial-b"])

    coordinator.announce("trial-a", "dead-token", "host-a", 12345)
    coordinator.abort_announcement("trial-a", "dead-token")
    coordinator.announce("trial-b", "token-b", "host-b", None)

    assert coordinator.get_session("trial-b", "token-b") is None

    # A stale abort from the dead process cannot erase a newer attempt from the same member.
    coordinator.announce("trial-a", "fresh-token", "host-a", 54321)
    coordinator.abort_announcement("trial-a", "dead-token")
    assert coordinator.get_session("trial-a", "fresh-token") == {
        "session_id": 0,
        "member_id": 0,
        "main_address": "host-a",
        "main_port": 54321,
    }


def test_coordinator_rejects_malformed_population_and_reused_invocation_token() -> None:
    """Population identity must be complete/unique and completed invocation tokens stay one-use."""

    coordinator = ClanCoordinator(population_size=2)

    with pytest.raises(ValueError, match="complete Tune population"):
        coordinator.register_trials(["trial-a"])
    with pytest.raises(ValueError, match="unique"):
        coordinator.register_trials(["trial-a", "trial-a"])

    coordinator.register_trials(["trial-a", "trial-b"])
    coordinator.announce("trial-a", "token-a", "host-a", 12345)
    coordinator.announce("trial-b", "token-b", "host-b", None)

    with pytest.raises(RuntimeError, match="reuse"):
        coordinator.announce("trial-a", "token-a", "host-a", 54321)
