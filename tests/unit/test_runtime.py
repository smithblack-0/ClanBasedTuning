"""Unit contracts for scheduler-owned cohort identity and rendezvous state."""

import pytest

from clan_based_tuning.runtime import ClanRuntimeSpec, _ClanCoordinator, _RuntimeRegistry


def _runtime_spec(name="coordinator-a"):
    return ClanRuntimeSpec(
        coordinator_name=name,
        population_size=2,
        metric="val_loss",
        mode="min",
        join_timeout_s=60.0,
        poll_interval_s=0.05,
    )


def test_registry_accepts_idempotent_registration_and_rejects_conflicting_clan():
    registry = _RuntimeRegistry()
    first = _runtime_spec()

    registry.register_trials(["trial-b", "trial-a"], first)
    registry.register_trials(["trial-b", "trial-a"], first)

    assert registry.get_runtime_spec("trial-a") == first
    assert registry.get_runtime_spec("trial-b") == first

    with pytest.raises(RuntimeError, match="another Clan runtime"):
        registry.register_trials(["trial-a"], _runtime_spec("coordinator-b"))


def test_coordinator_assigns_stable_members_and_opens_only_complete_sessions():
    coordinator = _ClanCoordinator(population_size=2)
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


def test_coordinator_rejects_malformed_population_and_reused_invocation_token():
    coordinator = _ClanCoordinator(population_size=2)

    with pytest.raises(ValueError, match="complete Tune population"):
        coordinator.register_trials(["trial-a"])
    with pytest.raises(ValueError, match="unique"):
        coordinator.register_trials(["trial-a", "trial-a"])

    coordinator.register_trials(["trial-a", "trial-b"])
    coordinator.announce("trial-a", "token-a", "host-a", 12345)
    coordinator.announce("trial-b", "token-b", "host-b", None)

    with pytest.raises(RuntimeError, match="reuse"):
        coordinator.announce("trial-a", "token-a", "host-a", 54321)
