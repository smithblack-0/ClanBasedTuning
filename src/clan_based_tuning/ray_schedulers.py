"""Small Ray Tune scheduler decorators used by Clan orchestration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ray.tune.schedulers import TrialScheduler

if TYPE_CHECKING:
    from ray.tune.execution.tune_controller import TuneController
    from ray.tune.experiment import Trial


logger = logging.getLogger(__name__)


class ClanCollectiveFailureScheduler(TrialScheduler):
    """Stop the Tune experiment when one required trial fails or is removed.

    Ordinary scheduling decisions and planned completion remain the responsibility
    of the composed scheduler. The supported Clan workflow disables Ray trial
    retries so the originating failure remains visible in the Tune result.
    """

    def __init__(self, *, downstream: TrialScheduler):
        if not isinstance(downstream, TrialScheduler):
            raise TypeError("downstream must be a Ray TrialScheduler")
        super().__init__()
        self._downstream = downstream
        self._supports_buffered_results = downstream.supports_buffered_results

    def set_search_properties(
        self,
        metric: str | None,
        mode: str | None,
        **spec: Any,
    ) -> bool:
        """Configure this decorator and its downstream scheduler consistently."""

        if not self._downstream.set_search_properties(metric, mode, **spec):
            return False
        return super().set_search_properties(metric, mode, **spec)

    def on_trial_add(self, tune_controller: TuneController, trial: Trial):
        """Forward trial admission without changing downstream policy."""

        return self._downstream.on_trial_add(tune_controller, trial)

    def on_trial_error(self, tune_controller: TuneController, trial: Trial):
        """Request collective stop and preserve downstream error notification."""

        self._request_collective_stop(tune_controller, trial, event="error")
        return self._downstream.on_trial_error(tune_controller, trial)

    def on_trial_result(
        self,
        tune_controller: TuneController,
        trial: Trial,
        result: dict[str, Any],
    ) -> str:
        """Return the downstream decision for an ordinary trial result."""

        return self._downstream.on_trial_result(tune_controller, trial, result)

    def on_trial_complete(
        self,
        tune_controller: TuneController,
        trial: Trial,
        result: dict[str, Any],
    ):
        """Leave natural and synchronized completion with the downstream owner."""

        return self._downstream.on_trial_complete(tune_controller, trial, result)

    def on_trial_remove(self, tune_controller: TuneController, trial: Trial):
        """Request collective stop and preserve downstream removal notification."""

        self._request_collective_stop(tune_controller, trial, event="remove")
        return self._downstream.on_trial_remove(tune_controller, trial)

    def choose_trial_to_run(self, tune_controller: TuneController) -> Trial | None:
        """Return the downstream scheduler's next trial choice."""

        return self._downstream.choose_trial_to_run(tune_controller)

    def debug_string(self) -> str:
        """Describe the collective failure decorator and downstream scheduler."""

        return f"Clan collective failure fan-out; {self._downstream.debug_string()}"

    def save(self, checkpoint_path: str):
        """Delegate persistence because this decorator owns no mutable state."""

        return self._downstream.save(checkpoint_path)

    def restore(self, checkpoint_path: str):
        """Delegate restoration because this decorator owns no mutable state."""

        return self._downstream.restore(checkpoint_path)

    @staticmethod
    def _request_collective_stop(
        tune_controller: TuneController,
        trial: Trial,
        *,
        event: str,
    ) -> None:
        logger.error(
            "Clan member lifecycle invalidated: event=%s trial_id=%s status=%s",
            event,
            trial.trial_id,
            trial.status,
        )
        tune_controller.request_stop_experiment()


__all__ = ["ClanCollectiveFailureScheduler"]
