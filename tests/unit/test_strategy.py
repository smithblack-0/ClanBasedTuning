from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
from lightning.pytorch.strategies import DDPStrategy

from clan_based_tuning import ClanDDPStrategy, apply_optimizer_strategy
from clan_based_tuning.lightning.environment import _ClanRuntime
from clan_based_tuning.spec import _ClanMetadata


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
    metadata = _ClanMetadata(population_size=2, rendezvous_name="test-clan")
    config = {"lr": 0.1}
    metadata.bind_trial_config(config)
    return ClanDDPStrategy(
        metadata,
        config,
        _runtime(),
        apply_optimizer_strategy,
        **ddp_kwargs,
    )


def test_strategy_supplies_required_ddp_settings_without_hiding_environment():
    strategy = _strategy()

    assert strategy._ddp_kwargs["init_sync"] is False
    assert strategy._ddp_kwargs["broadcast_buffers"] is False
    assert strategy.cluster_environment is None


def test_strategy_supplies_cross_trial_topology_to_automatic_samplers():
    metadata = _ClanMetadata(population_size=2, rendezvous_name="test-clan")
    config = {"lr": 0.1}
    metadata.bind_trial_config(config)
    strategy = ClanDDPStrategy(
        metadata,
        config,
        _runtime(global_rank=1),
        apply_optimizer_strategy,
    )

    assert strategy.distributed_sampler_kwargs == {"num_replicas": 2, "rank": 1}


def test_strategy_rejects_explicit_conflicting_ddp_settings():
    with pytest.raises(ValueError, match="init_sync=False"):
        _strategy(init_sync=True)

    with pytest.raises(ValueError, match="broadcast_buffers=False"):
        _strategy(broadcast_buffers=True)


def test_strategy_rejects_an_ignored_ray_checkpoint():
    metadata = _ClanMetadata(population_size=2, rendezvous_name="test-clan")
    config = {"lr": 0.1}
    metadata.bind_trial_config(config)
    strategy = ClanDDPStrategy(
        metadata,
        config,
        _runtime(checkpoint_available=True),
        apply_optimizer_strategy,
    )
    strategy._lightning_module = SimpleNamespace(trainer=SimpleNamespace(ckpt_path=None))

    with pytest.raises(RuntimeError, match="Lightning was started without ckpt_path"):
        strategy._is_fresh_trial()


def test_target_config_is_applied_after_lightning_restores_optimizer(monkeypatch):
    metadata = _ClanMetadata(population_size=2, rendezvous_name="test-clan")
    config = {"lr": 0.2}
    metadata.bind_trial_config(config)
    applications = []

    def apply(optimizers, current_config):
        applications.append(optimizers[0].param_groups[0]["lr"])
        optimizers[0].param_groups[0]["lr"] = current_config["lr"]

    strategy = ClanDDPStrategy(metadata, config, _runtime(), apply)
    optimizer = torch.optim.SGD([torch.nn.Parameter(torch.tensor(1.0))], lr=9.0)
    strategy.optimizers = [optimizer]

    def restore_source_state(self, checkpoint):
        del checkpoint
        self.optimizers[0].param_groups[0]["lr"] = 0.05

    monkeypatch.setattr(DDPStrategy, "load_optimizer_state_dict", restore_source_state)

    strategy.load_optimizer_state_dict({})

    assert applications == [0.05]
    assert optimizer.param_groups[0]["lr"] == pytest.approx(0.2)
