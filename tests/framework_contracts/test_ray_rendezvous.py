"""Contract tests for fresh cross-trial process-group sessions."""

import asyncio

import pytest

pytest.importorskip("ray")

from clan_based_tuning.ray_rendezvous import ProcessGroupRendezvous


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_rendezvous_returns_one_endpoint_and_distinct_ranks():
    async def scenario():
        rendezvous = ProcessGroupRendezvous(member_ids=[0, 1], timeout_s=1.0)
        first = asyncio.create_task(
            rendezvous.join(
                member_id=0,
                token="zero-0",
                host="10.0.0.1",
                port=4321,
            )
        )
        await asyncio.sleep(0)
        assert not first.done()
        second = asyncio.create_task(
            rendezvous.join(
                member_id=1,
                token="one-0",
                host="10.0.0.2",
                port=None,
            )
        )
        return await asyncio.gather(first, second)

    groups = asyncio.run(scenario())
    assert [group.global_rank for group in groups] == [0, 1]
    assert [group.session_id for group in groups] == [0, 0]
    assert [group.world_size for group in groups] == [2, 2]
    assert [group.master_address for group in groups] == ["10.0.0.1", "10.0.0.1"]
    assert [group.master_port for group in groups] == [4321, 4321]


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_rendezvous_requires_fresh_tokens_for_later_window():
    async def scenario():
        rendezvous = ProcessGroupRendezvous(member_ids=[0, 1], timeout_s=1.0)
        await asyncio.gather(
            rendezvous.join(
                member_id=0,
                token="zero-0",
                host="127.0.0.1",
                port=4321,
            ),
            rendezvous.join(
                member_id=1,
                token="one-0",
                host="127.0.0.1",
                port=None,
            ),
        )
        await rendezvous.join(
            member_id=0,
            token="zero-0",
            host="127.0.0.1",
            port=4322,
        )

    with pytest.raises(RuntimeError, match="cannot be reused"):
        asyncio.run(scenario())


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_rendezvous_times_out_with_missing_member_identity():
    async def scenario():
        rendezvous = ProcessGroupRendezvous(member_ids=[0, 1], timeout_s=0.01)
        await rendezvous.join(
            member_id=0,
            token="zero-0",
            host="127.0.0.1",
            port=4321,
        )

    with pytest.raises(RuntimeError, match=r"members \[1\]"):
        asyncio.run(scenario())


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_rendezvous_requires_contiguous_ddp_ranks():
    with pytest.raises(ValueError, match="contiguous"):
        ProcessGroupRendezvous(member_ids=[1, 2], timeout_s=1.0)


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_rendezvous_rejects_one_token_for_two_processes():
    async def scenario():
        rendezvous = ProcessGroupRendezvous(member_ids=[0, 1], timeout_s=1.0)
        first = asyncio.create_task(
            rendezvous.join(
                member_id=0,
                token="same",
                host="127.0.0.1",
                port=4321,
            )
        )
        await asyncio.sleep(0)
        try:
            await rendezvous.join(
                member_id=1,
                token="same",
                host="127.0.0.1",
                port=None,
            )
        finally:
            first.cancel()

    with pytest.raises(RuntimeError, match="another member"):
        asyncio.run(scenario())
