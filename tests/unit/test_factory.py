from __future__ import annotations

from types import SimpleNamespace

from clan_based_tuning import make_clan_lightning_plugins
from clan_based_tuning.lightning import ClanDDPStrategy, ClanLightningEnvironment
from clan_based_tuning.lightning.environment import _ClanRuntime
from clan_based_tuning.spec import _ClanMetadata


def test_factory_returns_concrete_lightning_units(monkeypatch):
    metadata = _ClanMetadata(population_size=2, rendezvous_name="test-clan")
    config = {"lr": 0.1}
    metadata.bind_trial_config(config)
    callback = SimpleNamespace(name="report")
    monkeypatch.setattr(
        "clan_based_tuning.factory._tune_report_callback",
        lambda **kwargs: callback,
    )
    runtime = _ClanRuntime(
        trial_id="trial-a",
        actor_token="actor-a",
        session_id=0,
        global_rank=0,
        world_size=2,
        master_address="127.0.0.1",
        master_port=12345,
    )

    monkeypatch.setattr(
        "clan_based_tuning.factory._resolve_tune_runtime",
        lambda metadata: runtime,
    )

    plugins = make_clan_lightning_plugins(
        config,
        metrics={"fitness": "val_loss"},
    )

    assert isinstance(plugins.strategy, ClanDDPStrategy)
    assert isinstance(plugins.environment, ClanLightningEnvironment)
    assert plugins.report_callback is callback
