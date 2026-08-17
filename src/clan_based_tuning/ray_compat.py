"""Narrow compatibility boundary for Tune trial continuation transfer.

ClanScheduler owns the Clan algorithm, but Tune does not expose a stable public atomic
operation for "resume this trial from that trial's checkpoint with this new config." The few
Developer/private operations needed to reproduce that transition live here and nowhere else.

This module is intentionally small even when individual functions are only a few lines: each
function names one unsupported upstream operation that may need repair when Ray changes. Do
not move selection, mutation, cohort, or Lightning policy into this layer; doing so would turn
a compatibility adapter back into a fork of PBT/Tune internals.
"""

import copy
from collections.abc import Callable
from typing import Any

from ray.train._internal.session import _FutureTrainingResult, _TrainingResult
from ray.tune import Checkpoint
from ray.tune.experiment import Trial

# Helpers


def _resolve_scheduled_checkpoint(
    scheduled: Checkpoint | _FutureTrainingResult | None,
) -> Checkpoint | None:
    """Normalize the two checkpoint shapes produced by Tune's internal save path.

    A scheduler-triggered save may already be a concrete checkpoint or may still be wrapped in
    Ray's asynchronous ``_FutureTrainingResult``. Keeping this normalization local prevents the
    Clan scheduler from depending on that private result-wrapper shape.
    """

    if not isinstance(scheduled, _FutureTrainingResult):
        return scheduled

    training_result = scheduled.resolve()
    if training_result is None:
        return None
    return training_result.checkpoint


# Main


def capture_trial_checkpoint(
    tune_controller: Any,
    trial: Trial,
    result: dict[str, Any],
    _resolve_checkpoint: Callable[
        [Checkpoint | _FutureTrainingResult | None], Checkpoint | None
    ] = _resolve_scheduled_checkpoint,
) -> Checkpoint:
    """Materialize the selected parent's exact boundary state before children are reassigned.

    Early-reporting trials may already be paused with a save in flight; the last reporter may
    still be running inside the scheduler callback. Ray PBT handles those states differently,
    so this adapter mirrors that distinction instead of asking for a duplicate save. The
    returned checkpoint is concrete because every child continuation must reference one stable
    parent artifact before the generation gate opens.

    Raises:
        RuntimeError: If the selected boundary produces no checkpoint to inherit.
    """

    if trial.status == Trial.PAUSED:
        saving_to = trial.temporary_state.saving_to
        scheduled = saving_to if isinstance(saving_to, _FutureTrainingResult) else trial.checkpoint
    else:
        scheduled = tune_controller._schedule_trial_save(trial, result=result)

    checkpoint = _resolve_checkpoint(scheduled)
    if checkpoint is None:
        raise RuntimeError("selected Clan member did not provide a checkpoint at the boundary")
    return checkpoint


def pause_trial_without_checkpoint(tune_controller: Any, trial: Trial) -> None:
    """Pause a member without letting Tune create a second, member-local continuation.

    The selected parent checkpoint is captured once and later installed on every child. Using
    Tune's normal checkpoint-on-pause behavior here would create redundant candidate-specific
    saves and could make the wrong artifact look authoritative. The function remains separate
    despite its size because ``pause_trial(..., should_checkpoint=False)`` is an upstream
    compatibility seam, not Clan policy.
    """

    if trial.status != Trial.PAUSED:
        tune_controller.pause_trial(trial, should_checkpoint=False)


def assign_trial_continuation(
    trial: Trial,
    config: dict[str, Any],
    checkpoint: Checkpoint,
    checkpoint_metrics: dict[str, Any],
) -> None:
    """Install the config/checkpoint pair Tune will use for the member's next invocation.

    Tune currently has no public scheduler operation for replacing both pieces atomically, so
    this mirrors the checkpoint-manager state update used by PBT. Copying the checkpoint object
    gives each trial its own continuation record while all records still point at the same
    selected parent artifact. The metrics travel with that checkpoint because Tune's restore
    bookkeeping expects a complete ``_TrainingResult`` rather than a bare checkpoint.

    If a future Ray release changes checkpoint-manager internals, repair this function first;
    callers should not learn the new private layout.
    """

    trial.set_config(config)
    trial.run_metadata.checkpoint_manager._latest_checkpoint_result = _TrainingResult(
        checkpoint=copy.copy(checkpoint),
        metrics=checkpoint_metrics,
    )
