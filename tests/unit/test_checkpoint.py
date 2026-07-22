from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from clan_based_tuning.ray.checkpoint import tune_checkpoint_path


class _Checkpoint:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.entered = False
        self.exited = False

    @contextmanager
    def as_directory(self):
        self.entered = True
        try:
            yield str(self.directory)
        finally:
            self.exited = True


def _install_fake_ray(monkeypatch: pytest.MonkeyPatch, checkpoint) -> None:
    ray = ModuleType("ray")
    ray.tune = SimpleNamespace(get_checkpoint=lambda: checkpoint)
    monkeypatch.setitem(sys.modules, "ray", ray)


def test_tune_checkpoint_path_keeps_materialized_directory_alive(monkeypatch, tmp_path):
    checkpoint_file = tmp_path / "checkpoint"
    checkpoint_file.write_text("state", encoding="utf-8")
    checkpoint = _Checkpoint(tmp_path)
    _install_fake_ray(monkeypatch, checkpoint)

    with tune_checkpoint_path() as path:
        assert path == str(checkpoint_file)
        assert checkpoint.entered
        assert not checkpoint.exited

    assert checkpoint.exited


def test_tune_checkpoint_path_returns_none_for_fresh_trial(monkeypatch):
    _install_fake_ray(monkeypatch, None)

    with tune_checkpoint_path() as path:
        assert path is None
