"""Contract tests for the public manual Clan Tuning composition."""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("ray")
pytest.importorskip("lightning")

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def _load_example():
    path = Path(__file__).resolve().parents[2] / "examples" / "manual_clan_tuning.py"
    spec = importlib.util.spec_from_file_location("manual_clan_tuning", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scalar_members_use_distinct_training_and_identical_validation_data():
    example = _load_example()
    member_zero = object.__new__(example.ScalarClanTrainable)
    member_zero._member_id = 0
    member_one = object.__new__(example.ScalarClanTrainable)
    member_one._member_id = 1

    train_zero, validation_zero = member_zero.configure_dataloaders()
    train_one, validation_one = member_one.configure_dataloaders()

    assert next(iter(train_zero))[1].item() == 1.0
    assert next(iter(train_one))[1].item() == 3.0
    assert next(iter(validation_zero))[1].item() == 0.0
    assert next(iter(validation_one))[1].item() == 0.0
