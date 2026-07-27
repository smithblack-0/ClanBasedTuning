"""Ray Tune execution seam for one completed Clan round.

Each training process owns and advances its own ``ClanController``. This module
starts only after those process-local controllers have produced one transition
report each. It verifies that the reports describe one population decision, then
asks Ray to save the winner and assign that checkpoint with each member's local
next controller and optimizer state.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ray.train._internal.session import _TrainingResult
from ray.tune.experiment import Trial
from ray.tune.schedulers import FIFOScheduler, TrialScheduler
from ray.tune.utils.util import unflatten_dict

from clan_based_tuning.member_state import (
    CONTROLLER_STATE,
    NEXT_MEMBER_STATE,
    OPTIMIZER_CONFIG,
    WINNER_ID,
)

if TYPE_CHECKING:
    from ray.tune.execution.tune_controller import TuneController

    from clan_based_tuning.controller import ClanController


MEMBER_ID = "clan_member_id"
ROUND_INDEX = "clan_round_index"
FITNESS = "clan_fitness"

__all__ = [
    "MEMBER_ID",
    "NEXT_MEMBER_STATE",
    "ClanTrialScheduler",
    "MemberTransition",
    "apply_ray_transition",
]


@dataclass(frozen=True, slots=True)
class MemberTransition:
    """Plain process-local result consumed at one Tune round boundary."""

    round_index: int
    member_id: int
    winner_id: int
    fitness: float
    controller_state: dict[str, Any]
    optimizer_config: dict[str, float]

    @classmethod
    def from_controller(
        cls,
        *,
        completed_round_index: int,
        fitness: float,
        winner_id: int,
        controller: ClanController,
    ) -> MemberTransition:
        """Capture the one local state produced by a completed controller advance."""

        controller_state = controller.state_dict()
        if controller_state["round_index"] != completed_round_index + 1:
            raise RuntimeError("controller has not advanced past the completed round")
        return cls(
            round_index=completed_round_index,
            member_id=controller.member_id,
            winner_id=winner_id,
            fitness=fitness,
            controller_state=controller_state,
            optimizer_config=controller.get_config(),
        )

    @classmethod
    def from_result(cls, result: dict[str, Any]) -> MemberTransition:
        """Copy one transition from the flattened result Tune gives schedulers."""

        return cls(
            round_index=result[ROUND_INDEX],
            member_id=result[MEMBER_ID],
            winner_id=result[WINNER_ID],
            fitness=result[FITNESS],
            controller_state=_nested_result(result, CONTROLLER_STATE),
            optimizer_config=_nested_result(result, OPTIMIZER_CONFIG),
        )

    def as_result(self) -> dict[str, Any]:
        """Return the flat Tune result fields for this transition."""

        return {
            ROUND_INDEX: self.round_index,
            MEMBER_ID: self.member_id,
            WINNER_ID: self.winner_id,
            FITNESS: self.fitness,
            CONTROLLER_STATE: copy.deepcopy(self.controller_state),
            OPTIMIZER_CONFIG: dict(self.optimizer_config),
        }

    def as_next_member_state(self) -> dict[str, Any]:
        """Return the member-local state installed beside the winner checkpoint."""

        return {
            WINNER_ID: self.winner_id,
            CONTROLLER_STATE: copy.deepcopy(self.controller_state),
            OPTIMIZER_CONFIG: dict(self.optimizer_config),
        }


@dataclass(frozen=True, slots=True)
class _Arrival:
    trial: Trial
    result: dict[str, Any]
    transition: MemberTransition


ApplyTransition = Callable[["TuneController", tuple[_Arrival, ...]], None]


def _nested_result(result: dict[str, Any], key: str) -> dict[str, Any]:
    """Recover one mapping after Tune's ``flatten_dict`` result translation."""

    if key in result:
        return copy.deepcopy(result[key])

    prefix = f"{key}/"
    flattened = {
        flattened_key.removeprefix(prefix): copy.deepcopy(value)
        for flattened_key, value in result.items()
        if flattened_key.startswith(prefix)
    }
    if not flattened:
        raise KeyError(key)
    return unflatten_dict(flattened)


def apply_ray_transition(
    tune_controller: TuneController,
    arrivals: tuple[_Arrival, ...],
) -> None:
    """Execute one winner-only checkpoint transition through Ray 2.56.

    Ray's synchronous PBT implementation uses the same private save, pause, and
    checkpoint-assignment surfaces. Keeping them in this one function makes the
    version-sensitive boundary independently replaceable and contract-testable.
    """

    winner_id = arrivals[0].transition.winner_id
    winner = next(arrival for arrival in arrivals if arrival.transition.member_id == winner_id)
    checkpoint_future = tune_controller._schedule_trial_save(
        winner.trial,
        result=winner.result,
    )
    if checkpoint_future is None:
        raise RuntimeError("Ray did not schedule the winning member checkpoint")

    checkpoint_result = checkpoint_future.resolve()
    if checkpoint_result is None or checkpoint_result.checkpoint is None:
        raise RuntimeError("the winning member did not produce a checkpoint")

    for arrival in arrivals:
        tune_controller.pause_trial(arrival.trial, should_checkpoint=False)
        target_config = copy.deepcopy(arrival.trial.config)
        target_config[NEXT_MEMBER_STATE] = arrival.transition.as_next_member_state()
        arrival.trial.set_config(target_config)
        arrival.trial.run_metadata.checkpoint_manager._latest_checkpoint_result = _TrainingResult(
            checkpoint=copy.copy(checkpoint_result.checkpoint),
            metrics=copy.deepcopy(checkpoint_result.metrics),
        )


class ClanTrialScheduler(FIFOScheduler):
    """Collect process-local decisions and execute one native Tune transition."""

    def __init__(
        self,
        *,
        apply_transition: ApplyTransition = apply_ray_transition,
        final_round_index: int | None = None,
    ):
        super().__init__()
        if final_round_index is not None and final_round_index < 0:
            raise ValueError("the final Clan round index cannot be negative")
        self._apply_transition = apply_transition
        self._final_round_index = final_round_index
        self._pending_round: int | None = None
        self._arrivals: dict[int, _Arrival] = {}
        self._last_completed_round: int | None = None

    def on_trial_result(
        self,
        tune_controller: TuneController,
        trial: Trial,
        result: dict[str, Any],
    ) -> str:
        """Hold one report per live member, then execute their agreed decision."""

        transition = MemberTransition.from_result(result)
        if trial.config[MEMBER_ID] != transition.member_id:
            raise RuntimeError("Ray trial and Clan member identities disagree")
        if (
            self._last_completed_round is not None
            and transition.round_index <= self._last_completed_round
        ):
            raise RuntimeError("received a stale or duplicate completed Clan round")

        if self._pending_round is None:
            self._pending_round = transition.round_index
        elif transition.round_index != self._pending_round:
            raise RuntimeError("received interleaved Clan round results")
        if transition.member_id in self._arrivals:
            raise RuntimeError("member reported the same Clan round twice")

        self._arrivals[transition.member_id] = _Arrival(
            trial=trial,
            result=copy.deepcopy(result),
            transition=transition,
        )

        member_trials = self._member_trials(tune_controller)
        expected_members = set(member_trials)
        arrived_members = set(self._arrivals)
        if not arrived_members <= expected_members:
            raise RuntimeError("result identifies a member outside the Ray population")
        if arrived_members != expected_members:
            return TrialScheduler.NOOP

        arrivals = tuple(self._arrivals[member_id] for member_id in sorted(expected_members))
        winner_ids = {arrival.transition.winner_id for arrival in arrivals}
        if len(winner_ids) != 1:
            raise RuntimeError("process-local Clan controllers disagree on the winner")
        winner_id = next(iter(winner_ids))
        if winner_id not in expected_members:
            raise RuntimeError("the selected winner is outside the Ray population")

        if self._pending_round == self._final_round_index:
            tune_controller.request_stop_experiment()
        else:
            self._apply_transition(tune_controller, arrivals)
        self._last_completed_round = self._pending_round
        self._pending_round = None
        self._arrivals.clear()
        return TrialScheduler.NOOP

    def on_trial_error(self, tune_controller: TuneController, trial: Trial) -> None:
        """Invalidate the active Clan instead of silently shrinking it."""

        member_id = trial.config[MEMBER_ID]
        raise RuntimeError(f"active Clan member {member_id} failed")

    def debug_string(self) -> str:
        """Describe both the Clan boundary and inherited trial selection."""

        return "Clan round transitions with FIFO trial selection."

    @staticmethod
    def _member_trials(tune_controller: TuneController) -> dict[int, Trial]:
        trials = tune_controller.get_trials()
        if any(trial.is_finished() for trial in trials):
            raise RuntimeError("the active Ray population contains a finished member")

        member_trials = {trial.config[MEMBER_ID]: trial for trial in trials}
        if len(member_trials) != len(trials):
            raise RuntimeError("Ray population contains duplicate Clan member identities")
        if len(member_trials) < 2:
            raise RuntimeError("a Clan transition requires at least two Ray trials")
        return member_trials
