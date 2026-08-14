"""Unit contracts for experiment identity, stable members, and invocation rendezvous.

The cohort state is deliberately tested without Ray actors. These contracts establish that
concurrent experiments cannot collide in the registry and that a DDP session opens only for
one complete set of fresh invocation tokens.
"""

import pytest

from clan_based_tuning.cohort import ClanCoordinator, ClanRuntimeSpec, RuntimeRegistry


def _runtime_spec(
    coordinator_name: str = "coordinator-a",
    experiment_name: str = "experiment-a",
) -> ClanRuntimeSpec:
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


def test_registry_scopes_trial_ids_by_experiment_and_rejects_conflicts() -> None:
    """Identical trial IDs may belong to different experiments but not two Clans in one run."""

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


def test_coordinator_assigns_stable_members_and_opens_only_complete_sessions() -> None:
    """Sorted trial identity fixes ranks and a session waits for every registered member."""

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


def test_coordinator_rejects_malformed_population_and_reused_invocation_token() -> None:
    """Malformed registration and reuse of a completed invocation identity fail immediately."""

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
