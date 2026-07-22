from __future__ import annotations

import pytest

from clan_based_tuning import ClanDDPStrategy, ClanRuntime, ClanSpec, OptimizerField


def _runtime() -> ClanRuntime:
    return ClanRuntime(
        trial_id="trial-a",
        actor_token="actor-a",
        session_id=0,
        global_rank=0,
        world_size=2,
        master_address="127.0.0.1",
        master_port=12345,
    )


def _spec() -> ClanSpec:
    return ClanSpec(
        population_size=2,
        optimizer_fields=(OptimizerField("lr", "lr"),),
        rendezvous_name="test-clan",
    )


def test_strategy_supplies_required_ddp_settings():
    strategy = ClanDDPStrategy(_spec(), {"lr": 0.1}, runtime=_runtime())

    assert strategy._ddp_kwargs["init_sync"] is False
    assert strategy._ddp_kwargs["broadcast_buffers"] is False
    assert strategy.cluster_environment.creates_processes_externally is True


def test_strategy_rejects_explicit_conflicting_ddp_settings():
    with pytest.raises(ValueError, match="init_sync=False"):
        ClanDDPStrategy(
            _spec(),
            {"lr": 0.1},
            runtime=_runtime(),
            init_sync=True,
        )

    with pytest.raises(ValueError, match="broadcast_buffers=False"):
        ClanDDPStrategy(
            _spec(),
            {"lr": 0.1},
            runtime=_runtime(),
            broadcast_buffers=True,
        )


def test_strategy_preserves_untuned_tuple_elements_in_schema():
    clan = ClanSpec(
        population_size=2,
        optimizer_fields=(OptimizerField("beta1", "betas", tuple_index=0),),
        rendezvous_name="test-clan",
    )
    strategy = ClanDDPStrategy(
        clan,
        {"beta1": 0.8},
        runtime=_runtime(),
    )

    assert strategy._optimizer_static_value(0, "betas", (0.9, 0.999)) == (
        "<clan-tuned>",
        0.999,
    )


def test_strategy_rejects_an_ignored_ray_checkpoint():
    from types import SimpleNamespace

    runtime = ClanRuntime(
        trial_id="trial-a",
        actor_token="actor-a",
        session_id=0,
        global_rank=0,
        world_size=2,
        master_address="127.0.0.1",
        master_port=12345,
        checkpoint_available=True,
    )
    strategy = ClanDDPStrategy(_spec(), {"lr": 0.1}, runtime=runtime)
    strategy._lightning_module = SimpleNamespace(
        trainer=SimpleNamespace(ckpt_path=None)
    )

    with pytest.raises(RuntimeError, match="Lightning was started without ckpt_path"):
        strategy._is_fresh_trial()
