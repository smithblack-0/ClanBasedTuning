import pytest

from clan_based_tuning.ray.round_store import CompletedRoundStore


def completed_record(member_id, round_index, fitness, *, learning_rate):
    return {
        "member_id": member_id,
        "round_index": round_index,
        "config": {"lr": learning_rate},
        "fitness": fitness,
    }


def test_population_is_unavailable_until_every_member_publishes():
    store = CompletedRoundStore(population_size=3)
    store.publish(2, completed_record(2, 0, 3.0, learning_rate=0.3))
    store.publish(0, completed_record(0, 0, 1.0, learning_rate=0.1))

    assert store.read_population(member_id=0, round_index=0) is None

    store.publish(1, completed_record(1, 0, 2.0, learning_rate=0.2))
    population = store.read_population(member_id=0, round_index=0)

    assert [record["member_id"] for record in population] == [0, 1, 2]
    assert [record["fitness"] for record in population] == [1.0, 2.0, 3.0]


def test_every_member_receives_an_independent_snapshot_before_round_closes():
    store = CompletedRoundStore(population_size=2)
    store.publish(0, completed_record(0, 4, 1.0, learning_rate=0.1))
    store.publish(1, completed_record(1, 4, 2.0, learning_rate=0.2))

    first = store.read_population(member_id=0, round_index=4)
    first[0]["config"]["lr"] = 9.0

    repeated = store.read_population(member_id=0, round_index=4)
    second = store.read_population(member_id=1, round_index=4)

    assert repeated[0]["config"] == {"lr": 0.1}
    assert second[0]["config"] == {"lr": 0.1}
    with pytest.raises(RuntimeError, match="already closed"):
        store.read_population(member_id=0, round_index=4)


def test_duplicate_or_mismatched_publication_fails_before_population_release():
    store = CompletedRoundStore(population_size=2)
    record = completed_record(0, 0, 1.0, learning_rate=0.1)
    store.publish(0, record)

    with pytest.raises(RuntimeError, match="more than once"):
        store.publish(0, record)
    with pytest.raises(RuntimeError, match="does not match"):
        store.publish(1, record)


def test_closed_round_rejects_late_publication_without_blocking_the_next_round():
    store = CompletedRoundStore(population_size=2)
    for member_id in range(2):
        store.publish(
            member_id,
            completed_record(member_id, 0, float(member_id), learning_rate=0.1),
        )
    for member_id in range(2):
        assert store.read_population(member_id=member_id, round_index=0) is not None

    with pytest.raises(RuntimeError, match="already closed"):
        store.publish(0, completed_record(0, 0, 1.0, learning_rate=0.1))

    store.publish(0, completed_record(0, 1, 1.0, learning_rate=0.1))
    assert store.read_population(member_id=0, round_index=1) is None


def test_invalid_transport_record_is_rejected_at_the_store_boundary():
    store = CompletedRoundStore(population_size=2)

    with pytest.raises(ValueError, match="finite"):
        store.publish(0, completed_record(0, 0, float("nan"), learning_rate=0.1))
    with pytest.raises(ValueError, match="member_id"):
        store.publish(2, completed_record(2, 0, 1.0, learning_rate=0.1))
