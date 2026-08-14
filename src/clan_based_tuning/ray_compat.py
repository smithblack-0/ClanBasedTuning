"""Narrow compatibility boundary for Tune trial state transfer.

ClanScheduler owns its synchronous generation algorithm instead of subclassing Ray's PBT
implementation. Tune currently exposes scheduler lifecycle callbacks but not a public atomic
operation for "resume this trial from that trial's checkpoint and config". The few Developer
or private Ray operations required for that transfer live only in this module so future Ray
changes require one compatibility repair rather than a scheduler redesign.

The behavior mirrors the corresponding synchronous-PBT operations in Ray Tune. No mutation,
selection, cohort, or Lightning policy belongs here.
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
    """Resolve Tune's asynchronous save wrapper while preserving direct checkpoints."""

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
    """Return the checkpoint representing ``trial`` at its current scheduler boundary.

    Args:
        tune_controller: Active Tune controller supplying the internal save operation.
        trial: Selected parent trial whose just-reported state must become the continuation.
        result: Selected parent result associated with the boundary checkpoint.
        _resolve_checkpoint: Injectable save-result resolver for isolated compatibility tests.

    Returns:
        Concrete Tune checkpoint containing the selected boundary state.

    Raises:
        RuntimeError: If the boundary produced no checkpoint to inherit.
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
    """Pause one running trial without asking Tune to create a duplicate checkpoint.

    Args:
        tune_controller: Active Tune controller owning trial execution state.
        trial: Clan member to pause at the completed generation boundary.
    """

    if trial.status != Trial.PAUSED:
        tune_controller.pause_trial(trial, should_checkpoint=False)


def assign_trial_continuation(
    trial: Trial,
    config: dict[str, Any],
    checkpoint: Checkpoint,
    checkpoint_metrics: dict[str, Any],
) -> None:
    """Assign the config and inherited checkpoint Tune will use when a member resumes.

    Args:
        trial: Clan member receiving the selected continuation.
        config: Independently mutated child Tune config for this stable member.
        checkpoint: Selected parent's concrete Tune checkpoint.
        checkpoint_metrics: Selected parent's boundary metrics stored with the checkpoint.

    Ray PBT performs the same checkpoint-manager update internally. Keeping it here makes the
    unsupported Tune detail explicit while the Clan scheduler remains independent of PBT's
    private class layout and mutation implementation.
    """

    trial.set_config(config)
    trial.run_metadata.checkpoint_manager._latest_checkpoint_result = _TrainingResult(
        checkpoint=copy.copy(checkpoint),
        metrics=checkpoint_metrics,
    )
