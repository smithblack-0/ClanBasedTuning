"""Execute unanimous process-local Clan decisions through Ray Tune."""

from __future__ import annotations

import copy

from ray.tune.schedulers import FIFOScheduler, TrialScheduler

CLAN_MEMBER_ID = "__clan_member_id"
CLAN_ROUND_INDEX = "__clan_round_index"
CLAN_WINNER_ID = "__clan_winner_id"
CLAN_NEXT_CONFIG = "__clan_next_config"
_NEXT_CONFIG_PREFIX = f"{CLAN_NEXT_CONFIG}/"


class ClanTransitionScheduler(FIFOScheduler):
    """Execute one agreed Clan transition without owning population policy.

    Every member reports the winner it independently observed and only its own
    next controlled values. The scheduler waits for one report from every member,
    rejects disagreement, asks Ray to checkpoint the winning live process once,
    and assigns that checkpoint plus each receiving member's values through Ray's
    native trial lifecycle.

    Training, fitness comparison, winner selection, and optimizer mutation remain
    process-local responsibilities. Ray remains responsible for trial execution,
    checkpoint transfer, configuration assignment, pause, and resume.
    """

    _supports_buffered_results = False

    def __init__(self, *, population_size: int):
        super().__init__()
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        self.population_size = population_size
        self._reports_by_round = {}
        self._completed_rounds = set()

    def on_trial_result(self, tune_controller, trial, result):
        """Hold the population at one boundary, then execute its agreed transition."""

        report = self._read_report(trial, result)
        round_index = report["round_index"]
        if round_index in self._completed_rounds:
            raise RuntimeError(f"round {round_index} reported after its transition completed")

        round_reports = self._reports_by_round.setdefault(round_index, {})
        member_id = report["member_id"]
        if member_id in round_reports:
            raise RuntimeError(f"member {member_id} reported round {round_index} twice")
        round_reports[member_id] = (trial, report, dict(result))

        if len(round_reports) < self.population_size:
            return TrialScheduler.NOOP

        self._execute_transition(tune_controller, round_index, round_reports)
        del self._reports_by_round[round_index]
        self._completed_rounds.add(round_index)
        return TrialScheduler.NOOP

    def _read_report(self, trial, result):
        member_id = result[CLAN_MEMBER_ID]
        round_index = result[CLAN_ROUND_INDEX]
        winner_id = result[CLAN_WINNER_ID]
        expected_ids = range(self.population_size)

        if not isinstance(member_id, int) or member_id not in expected_ids:
            raise RuntimeError(f"invalid Clan member id: {member_id!r}")
        if not isinstance(round_index, int) or round_index < 0:
            raise RuntimeError(f"invalid Clan round index: {round_index!r}")
        if not isinstance(winner_id, int) or winner_id not in expected_ids:
            raise RuntimeError(f"invalid Clan winner id: {winner_id!r}")
        if trial.config[CLAN_MEMBER_ID] != member_id:
            raise RuntimeError("reported Clan member id disagrees with the Ray trial config")
        if trial.config[CLAN_ROUND_INDEX] != round_index:
            raise RuntimeError("reported Clan round index disagrees with the Ray trial config")

        next_config = {
            key.removeprefix(_NEXT_CONFIG_PREFIX): value
            for key, value in result.items()
            if key.startswith(_NEXT_CONFIG_PREFIX)
        }
        if not next_config:
            raise RuntimeError("Clan transition report contains no next controlled values")
        return {
            "member_id": member_id,
            "round_index": round_index,
            "winner_id": winner_id,
            "next_config": next_config,
        }

    def _execute_transition(self, tune_controller, round_index, reports):
        expected_ids = set(range(self.population_size))
        if set(reports) != expected_ids:
            raise RuntimeError("Clan transition population is incomplete")

        winner_ids = {report["winner_id"] for _, report, _ in reports.values()}
        if len(winner_ids) != 1:
            raise RuntimeError("Clan members disagree about the winning member")
        winner_id = winner_ids.pop()
        winner_trial, _, winner_result = reports[winner_id]

        checkpoint_future = tune_controller._schedule_trial_save(
            winner_trial,
            result=winner_result,
        )
        winner_checkpoint = checkpoint_future.resolve()
        if winner_checkpoint is None or winner_checkpoint.checkpoint is None:
            raise RuntimeError("winning member did not produce an assignable checkpoint")

        for _, (target_trial, report, _) in sorted(reports.items()):
            next_trial_config = dict(target_trial.config)
            next_trial_config.update(report["next_config"])
            next_trial_config[CLAN_ROUND_INDEX] = round_index + 1

            if target_trial.status == target_trial.RUNNING:
                tune_controller.pause_trial(target_trial, should_checkpoint=False)
            target_trial.set_config(next_trial_config)
            target_trial.run_metadata.checkpoint_manager._latest_checkpoint_result = copy.copy(
                winner_checkpoint
            )
