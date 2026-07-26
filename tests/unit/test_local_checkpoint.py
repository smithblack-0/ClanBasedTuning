from types import SimpleNamespace

import pytest

from clan_based_tuning.lightning.checkpoint import save_local_checkpoint


def test_local_checkpoint_uses_lightning_dump_and_strategy_write_without_barrier(tmp_path):
    calls = []
    checkpoint = {"state_dict": {"weight": 1.0}, "optimizer_states": [{"step": 2}]}
    trainer = SimpleNamespace(
        model=object(),
        _checkpoint_connector=SimpleNamespace(
            dump_checkpoint=lambda weights_only: calls.append(("dump", weights_only))
            or checkpoint
        ),
        strategy=SimpleNamespace(
            save_checkpoint=lambda state, path, storage_options=None: calls.append(
                ("save", state, path, storage_options)
            ),
            barrier=lambda name: calls.append(("barrier", name)),
        ),
    )
    path = tmp_path / "winner.ckpt"

    save_local_checkpoint(trainer, path)

    assert calls == [
        ("dump", None),
        ("save", checkpoint, path, None),
    ]


def test_local_checkpoint_requires_an_attached_model(tmp_path):
    trainer = SimpleNamespace(model=None)

    with pytest.raises(AttributeError, match="model is attached"):
        save_local_checkpoint(trainer, tmp_path / "winner.ckpt")
