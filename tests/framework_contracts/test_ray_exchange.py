"""Contract tests for the asynchronous Ray controller callback transport."""

import asyncio

import pytest

pytest.importorskip("ray")

from clan_based_tuning import ClanRound
from clan_based_tuning.ray_exchange import (
    PublishedRound,
    RayControllerCallbacks,
    RoundExchange,
)


def _published(member_id, *, round_index=0, fitness=None):
    return PublishedRound(
        member_id=member_id,
        round_index=round_index,
        config={"lr": float(member_id + 1)},
        fitness=float(member_id if fitness is None else fitness),
    )


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_async_exchange_releases_every_loader_after_full_population():
    async def scenario():
        exchange = RoundExchange(member_ids=[0, 1], timeout_s=1.0)
        await exchange.publish(_published(0))
        first_load = asyncio.create_task(exchange.load(0))
        await asyncio.sleep(0)
        assert not first_load.done()

        await exchange.publish(_published(1))
        first_population, second_population = await asyncio.gather(
            first_load,
            exchange.load(0),
        )
        return first_population, second_population

    first, second = asyncio.run(scenario())
    assert first == second == [_published(0), _published(1)]


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_async_exchange_times_out_with_missing_member_identity():
    async def scenario():
        exchange = RoundExchange(member_ids=[0, 1], timeout_s=0.01)
        await exchange.publish(_published(0))
        await exchange.load(0)

    with pytest.raises(RuntimeError, match=r"round 0.*members \[1\]"):
        asyncio.run(scenario())


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_exchange_rejects_duplicate_member_identity():
    with pytest.raises(ValueError, match="unique"):
        RoundExchange(member_ids=[0, 0, 1], timeout_s=1.0)


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_exchange_rejects_disagreement_and_closed_round_reuse():
    async def disagreement():
        exchange = RoundExchange(member_ids=[0, 1], timeout_s=1.0)
        await exchange.publish(_published(0))
        await exchange.publish(_published(1))
        await exchange.announce(round_index=0, member_id=0, winner_id=0)
        await exchange.announce(round_index=0, member_id=1, winner_id=1)

    with pytest.raises(RuntimeError, match="disagree"):
        asyncio.run(disagreement())

    async def closed_reuse():
        exchange = RoundExchange(member_ids=[0, 1], timeout_s=1.0)
        await exchange.publish(_published(0))
        await exchange.publish(_published(1))
        assert not await exchange.announce(round_index=0, member_id=0, winner_id=1)
        assert await exchange.announce(round_index=0, member_id=1, winner_id=1)
        await exchange.publish(_published(0))

    with pytest.raises(RuntimeError, match="already closed"):
        asyncio.run(closed_reuse())


class RemoteCall:
    def __init__(self, call):
        self._call = call

    def remote(self, *args, **kwargs):
        return self._call(*args, **kwargs)


class FakeExchangeActor:
    def __init__(self):
        self.published = []
        self.announced = []
        self.population = [_published(0, fitness=1.0), _published(1, fitness=2.0)]
        self.publish = RemoteCall(self._publish)
        self.load = RemoteCall(self._load)
        self.announce = RemoteCall(self._announce)

    def _publish(self, round_):
        self.published.append(round_)

    def _load(self, round_index):
        assert round_index == 0
        return self.population

    def _announce(self, **announcement):
        self.announced.append(announcement)


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_callback_container_translates_controller_objects_and_call_order():
    exchange = FakeExchangeActor()
    callbacks = RayControllerCallbacks(
        exchange=exchange,
        member_id=0,
        resolve=lambda value: value,
    )
    local_round = ClanRound(
        member_id=0,
        round_index=0,
        config={"lr": 1.0},
        fitness=1.0,
        save_member_fitness=lambda round_: None,
    )

    callbacks.save_member_fitness(local_round)
    population = callbacks.load_population(0)
    callbacks.select_winner(0)

    assert exchange.published == [_published(0, fitness=1.0)]
    assert [(round_.member_id, round_.fitness) for round_ in population] == [
        (0, 1.0),
        (1, 2.0),
    ]
    assert exchange.announced == [{"round_index": 0, "member_id": 0, "winner_id": 0}]
    with pytest.raises(RuntimeError, match="cannot publish"):
        population[0].set_fitness(3.0)


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_callback_container_rejects_out_of_order_winner_selection():
    callbacks = RayControllerCallbacks(
        exchange=FakeExchangeActor(),
        member_id=0,
        resolve=lambda value: value,
    )

    with pytest.raises(RuntimeError, match="before loading"):
        callbacks.select_winner(0)
