"""Regression assertions for the explicit native Lightning/DDP contract probe."""

from __future__ import annotations

import pytest

from tests.framework_contracts.native_trial_lightning_probe import run_probe


@pytest.mark.framework_contract
def test_native_trials_load_one_winner_checkpoint_then_mutate_locally(tmp_path):
    report = run_probe(tmp_path)
    first, second = report["window_1"], report["window_2"]

    # Fresh members receive the same reduced gradient and apply local configs.
    assert first[0]["final"]["reduced_gradient"] == pytest.approx(2.0)
    assert first[1]["final"]["reduced_gradient"] == pytest.approx(2.0)
    assert first[0]["final"]["weight"] == pytest.approx(0.8)
    assert first[1]["final"]["weight"] == pytest.approx(0.6)
    assert first[0]["final"]["learning_rate"] == pytest.approx(0.1)
    assert first[1]["final"]["learning_rate"] == pytest.approx(0.2)

    # Rank 0 is the controller-selected winner. Rank 1 contributes no checkpoint.
    assert (tmp_path / "window-1" / "trial-0" / "winner.ckpt").is_file()
    assert not (tmp_path / "window-1" / "trial-1" / "winner.ckpt").exists()

    # Both reconstructed processes load the same complete winner state before their
    # local controllers manufacture next-round optimizer configurations.
    assert second[0]["start"]["global_step"] == 1
    assert second[1]["start"]["global_step"] == 1
    assert second[0]["start"]["weight"] == pytest.approx(0.8)
    assert second[1]["start"]["weight"] == pytest.approx(0.8)
    assert second[0]["start"]["momentum"] == pytest.approx(2.0)
    assert second[1]["start"]["momentum"] == pytest.approx(2.0)
    assert second[0]["start"]["learning_rate"] == pytest.approx(0.1)
    assert second[1]["start"]["learning_rate"] != pytest.approx(0.1)

    # Reformed DDP again supplies one gradient while optimizer variation diverges.
    assert second[0]["final"]["reduced_gradient"] == pytest.approx(1.6)
    assert second[1]["final"]["reduced_gradient"] == pytest.approx(1.6)
    assert second[0]["final"]["momentum"] == pytest.approx(3.4)
    assert second[1]["final"]["momentum"] == pytest.approx(3.4)
    for member in second:
        expected_weight = 0.8 - member["final"]["learning_rate"] * 3.4
        assert member["final"]["weight"] == pytest.approx(expected_weight)
    assert second[0]["final"]["weight"] != pytest.approx(second[1]["final"]["weight"])
