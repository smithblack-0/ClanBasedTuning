from __future__ import annotations

import json
import warnings

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
pytest.importorskip("ray")

from examples.iris_clan_experiment import REPORTS_PER_TRIAL, run_experiment


def test_initial_iris_workload_runs_through_public_manual_path(tmp_path):
    report = run_experiment(tmp_path)

    assert report["errors"] == []
    assert report["round_policy"]["completed_transitions"] == REPORTS_PER_TRIAL - 1
    assert len(report["selection_path"]) == REPORTS_PER_TRIAL - 1
    assert all(0.0 <= member["validation_accuracy"] <= 1.0 for member in report["members"])
    assert all(member["validation_loss"] >= 0.0 for member in report["members"])
    assert report["compute"]["elapsed_seconds"] > 0.0

    # The first qualifying run is intentionally emitted in the warning summary so its
    # exact neutral result can be copied into the reviewed experiment record.
    warnings.warn(
        "IRIS_CLAN_RESULT=" + json.dumps(report, sort_keys=True),
        UserWarning,
        stacklevel=1,
    )
