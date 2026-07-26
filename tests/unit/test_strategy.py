from __future__ import annotations

from types import SimpleNamespace

import pytest

from clan_based_tuning import ClanDDPStrategy
from clan_based_tuning.lightning.environment import _ClanRuntime


def _runtime(
    *,
    global_rank: int = 0,
    checkpoint_available: bool = False,
) -> _ClanRuntime:
    return _ClanRuntime(
        trial_id="trial-a",
        actor_token="actor-a",
        session_id=0,
        global_rank=global_rank,
        world_size=2,
        master_address="127.0.0.1",
        master_port=12345,
        checkpoint_available=checkpoint_available,
    )


def _strategy(**ddp_kwargs) -> ClanDDPStrategy:
    return ClanDDPStrategy(_runtime(), **ddp_kwargs)


def test_strategy_supplies_required_ddp_settings_without_hiding_environment():
    strategy = _strategy()

    assert strategy._ddp_kwargs["init_sync"] is False
    assert strategy._ddp_kwargs["broadcast_buffers"] is False
    assert strategy.cluster_environment is None


def test_strategy_supplies_cross_trial_topology_to_automatic_samplers():
    strategy = ClanDDPStrategy(_runtime(global_rank=1))

    assert strategy.distributed_sampler_kwargs == {"num_replicas": 2, "rank": 1}


def test_strategy_rejects_explicit_conflicting_ddp_settings():
    with pytest.raises(ValueError, match="init_sync=False"):
        _strategy(init_sync=True)

    with pytest.raises(ValueError, match="broadcast_buffers=False"):
        _strategy(broadcast_buffers=True)


def test_strategy_rejects_an_ignored_ray_checkpoint():
    strategy = ClanDDPStrategy(_runtime(checkpoint_available=True))
    strategy._lightning_module = SimpleNamespace(trainer=SimpleNamespace(ckpt_path=None))

    with pytest.raises(RuntimeError, match="Lightning was started without ckpt_path"):
        strategy._is_fresh_trial()


def test_strategy_allows_controller_selected_nonzero_rank_to_write(monkeypatch):
    strategy = ClanDDPStrategy(_runtime(global_rank=1))
    writes = []
    strategy._checkpoint_io = SimpleNamespace(
        save_checkpoint=lambda checkpoint, filepath, storage_options=None: writes.append(
            (checkpoint, filepath, storage_options)
        )
    )

    strategy.save_checkpoint({"state": 1}, "winner.ckpt")

    assert writes == [({"state": 1}, "winner.ckpt", None)]
