"""Focused tests for Clan-specific Ray scheduler decorators."""

from types import SimpleNamespace

import pytest

pytest.importorskip("ray")

from ray.tune.experiment import Trial
from ray.tune.schedulers import FIFOScheduler, TrialScheduler

from clan_based_tuning.ray_schedulers import ClanCollectiveFailureScheduler

pytestmark = pytest.mark.requires_ray


class RecordingScheduler(TrialScheduler):
    def __init__(self, *, supports_buffered_results=False):
        super().__init__()
        self._supports_buffered_results = supports_buffered_results
        self.calls = []
        self.choice = object()

    def set_search_properties(self, metric, mode, **spec):
        self.calls.append(("set_search_properties", metric, mode, spec))
        return super().set_search_properties(metric, mode, **spec)

    def on_trial_add(self, tune_controller, trial):
        self.calls.append(("add", tune_controller, trial))

    def on_trial_error(self, tune_controller, trial):
        self.calls.append(("error", tune_controller, trial))

    def on_trial_result(self, tune_controller, trial, result):
        self.calls.append(("result", tune_controller, trial, result))
        return self.PAUSE

    def on_trial_complete(self, tune_controller, trial, result):
        self.calls.append(("complete", tune_controller, trial, result))

    def on_trial_remove(self, tune_controller, trial):
        self.calls.append(("remove", tune_controller, trial))

    def choose_trial_to_run(self, tune_controller):
        self.calls.append(("choose", tune_controller))
        return self.choice

    def debug_string(self):
        return "recording scheduler"

    def save(self, checkpoint_path):
        self.calls.append(("save", checkpoint_path))
        return "saved"

    def restore(self, checkpoint_path):
        self.calls.append(("restore", checkpoint_path))
        return "restored"


class FakeTuneController:
    def __init__(self):
        self.stop_requested = False
        self.stop_request_count = 0

    def request_stop_experiment(self):
        self.stop_requested = True
        self.stop_request_count += 1


def _trial(trial_id="member-0", status=Trial.RUNNING):
    return SimpleNamespace(trial_id=trial_id, status=status)


def test_transparently_delegates_ordinary_scheduler_behavior():
    downstream = RecordingScheduler(supports_buffered_results=False)
    scheduler = ClanCollectiveFailureScheduler(downstream=downstream)
    controller = FakeTuneController()
    trial = _trial()
    result = {"fitness": 1.5}

    assert scheduler.set_search_properties("fitness", "min", custom="value")
    assert scheduler.metric == downstream.metric == "fitness"
    assert scheduler.supports_buffered_results is False
    assert scheduler.on_trial_add(controller, trial) is None
    assert scheduler.on_trial_result(controller, trial, result) == TrialScheduler.PAUSE
    assert scheduler.choose_trial_to_run(controller) is downstream.choice
    assert scheduler.on_trial_complete(controller, trial, result) is None
    assert scheduler.debug_string() == ("Clan collective failure fan-out; recording scheduler")
    assert controller.stop_requested is False

    assert downstream.calls == [
        ("set_search_properties", "fitness", "min", {"custom": "value"}),
        ("add", controller, trial),
        ("result", controller, trial, result),
        ("choose", controller),
        ("complete", controller, trial, result),
    ]


@pytest.mark.parametrize(
    ("callback_name", "status", "event"),
    [
        ("on_trial_error", Trial.RUNNING, "error"),
        ("on_trial_remove", Trial.PENDING, "remove"),
        ("on_trial_remove", Trial.PAUSED, "remove"),
    ],
)
def test_failure_or_removal_requests_collective_stop_and_records_context(
    callback_name,
    status,
    event,
    caplog,
):
    downstream = RecordingScheduler()
    scheduler = ClanCollectiveFailureScheduler(downstream=downstream)
    controller = FakeTuneController()
    trial = _trial(status=status)

    with caplog.at_level("ERROR", logger="clan_based_tuning.ray_schedulers"):
        getattr(scheduler, callback_name)(controller, trial)

    assert controller.stop_requested is True
    assert controller.stop_request_count == 1
    assert downstream.calls == [(event, controller, trial)]
    assert f"event={event}" in caplog.text
    assert "trial_id=member-0" in caplog.text
    assert f"status={status}" in caplog.text


def test_repeated_terminal_callbacks_rely_on_idempotent_controller_stop_flag():
    downstream = RecordingScheduler()
    scheduler = ClanCollectiveFailureScheduler(downstream=downstream)
    controller = FakeTuneController()
    trial = _trial()

    scheduler.on_trial_error(controller, trial)
    scheduler.on_trial_error(controller, trial)

    assert controller.stop_requested is True
    assert controller.stop_request_count == 2
    assert [call[0] for call in downstream.calls] == ["error", "error"]


def test_delegates_persistence_to_the_downstream_scheduler():
    downstream = RecordingScheduler()
    scheduler = ClanCollectiveFailureScheduler(downstream=downstream)

    assert scheduler.save("scheduler-state") == "saved"
    assert scheduler.restore("scheduler-state") == "restored"
    assert downstream.calls == [
        ("save", "scheduler-state"),
        ("restore", "scheduler-state"),
    ]


def test_fifo_persistence_remains_explicitly_unsupported():
    scheduler = ClanCollectiveFailureScheduler(downstream=FIFOScheduler())

    with pytest.raises(NotImplementedError):
        scheduler.save("scheduler-state")
    with pytest.raises(NotImplementedError):
        scheduler.restore("scheduler-state")


def test_rejects_a_non_scheduler_downstream():
    with pytest.raises(TypeError, match="TrialScheduler"):
        ClanCollectiveFailureScheduler(downstream=object())
