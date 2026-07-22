"""Regression assertions for the native-trial Lightning DDP contract probe."""

from __future__ import annotations

import pytest

from tests.framework_contracts.native_trial_lightning_probe import run_probe


@pytest.mark.framework_contract
def test_native_trials_can_checkpoint_exploit_restart_and_reform_ddp(tmp_path):
    report = run_probe(tmp_path)
    first, second = report["window_1"], report["window_2"]

    # The strategy synchronizes the fresh population once, then every trial
    # receives the same reduced gradient and applies its own optimizer config.
    assert first[0]["final"]["reduced_gradient"] == pytest.approx(2.0)
    assert first[1]["final"]["reduced_gradient"] == pytest.approx(2.0)
    assert first[0]["final"]["weight"] == pytest.approx(0.8)
    assert first[1]["final"]["weight"] == pytest.approx(0.6)
    assert first[0]["final"]["learning_rate"] == pytest.approx(0.1)
    assert first[1]["final"]["learning_rate"] == pytest.approx(0.2)

    # Every native trial has an authoritative checkpoint, even when its clan
    # rank is nonzero and Lightning would ordinarily suppress the write.
    assert (tmp_path / "window-1" / "trial-0" / "trial.ckpt").is_file()
    assert (tmp_path / "window-1" / "trial-1" / "trial.ckpt").is_file()

    # Both restarted processes load the source trial's complete state. The
    # target then applies its mutated trial configuration after optimizer load.
    assert second[0]["start"]["global_step"] == 1
    assert second[1]["start"]["global_step"] == 1
    assert second[0]["start"]["weight"] == pytest.approx(0.8)
    assert second[1]["start"]["weight"] == pytest.approx(0.8)
    assert second[0]["start"]["momentum"] == pytest.approx(2.0)
    assert second[1]["start"]["momentum"] == pytest.approx(2.0)
    assert second[0]["start"]["learning_rate"] == pytest.approx(0.1)
    assert second[1]["start"]["learning_rate"] == pytest.approx(0.3)

    # The reformed process group again supplies one common gradient, while the
    # inherited trials diverge according to their current configurations.
    assert second[0]["final"]["reduced_gradient"] == pytest.approx(1.6)
    assert second[1]["final"]["reduced_gradient"] == pytest.approx(1.6)
    assert second[0]["final"]["momentum"] == pytest.approx(3.4)
    assert second[1]["final"]["momentum"] == pytest.approx(3.4)
    assert second[0]["final"]["weight"] == pytest.approx(0.46)
    assert second[1]["final"]["weight"] == pytest.approx(-0.22)
