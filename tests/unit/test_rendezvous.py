from __future__ import annotations

import pytest

from clan_based_tuning.ray.rendezvous import RendezvousState


def test_rendezvous_assigns_one_session_after_full_population_arrives():
    state = RendezvousState(population_size=2)
    state.register_members(["trial-b", "trial-a"])

    state.announce("trial-a", "a-1", "10.0.0.1", 2345)
    assert state.get_session("trial-a", "a-1") is None

    state.announce("trial-b", "b-1", "10.0.0.2", None)
    first = state.get_session("trial-a", "a-1")
    second = state.get_session("trial-b", "b-1")

    assert first == {
        "session_id": 0,
        "global_rank": 0,
        "world_size": 2,
        "master_address": "10.0.0.1",
        "master_port": 2345,
    }
    assert second["global_rank"] == 1
    assert second["session_id"] == 0


def test_rendezvous_requires_new_actor_tokens_for_next_window():
    state = RendezvousState(population_size=2)
    state.register_members(["trial-a", "trial-b"])
    state.announce("trial-a", "a-1", "host", 1234)
    state.announce("trial-b", "b-1", "host", None)

    with pytest.raises(RuntimeError, match="cannot be reused"):
        state.announce("trial-a", "a-1", "host", 1235)

    state.announce("trial-a", "a-2", "host", 1235)
    state.announce("trial-b", "b-2", "host", None)
    assert state.get_session("trial-a", "a-2")["session_id"] == 1


def test_rendezvous_assigns_ranks_from_complete_sorted_trial_ids():
    state = RendezvousState(population_size=3)
    state.register_members(["trial-c", "trial-a", "trial-b"])

    assert state.member_ranks == {"trial-a": 0, "trial-b": 1, "trial-c": 2}
