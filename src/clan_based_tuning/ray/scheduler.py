"""Synchronous Ray PBT execution for controller-selected Clan transitions."""

from __future__ import annotations

from typing import Any

from clan_based_tuning.spec import CLAN_ROUND_RESULT_KEY, _ClanMetadata

try:
    from ray.tune.result import SHOULD_CHECKPOINT
    from ray.tune.schedulers import PopulationBasedTraining
except ModuleNotFoundError:
    PopulationBasedTraining = object  # type: ignore[assignment,misc]
    SHOULD_CHECKPOINT = "should_checkpoint"
    _RAY_AVAILABLE = False
else:
    _RAY_AVAILABLE = True


class ClanBasedTraining(PopulationBasedTraining):  # type: ignore[misc]
    """Reuse synchronous PBT execution while replacing its population policy.

    Each process-local ``ClanController`` receives the same completed population and
    reports the same selected winner. This scheduler verifies that agreement, asks
    native PBT to retain the winner's sole reported checkpoint, and assigns it to every
    losing target. Target Tune configs remain unchanged because local optimizer
    mutation occurs from controller state after Lightning restores the winner.
    """

    _supports_buffered_results = False

    def __init__(
        self,
        population_size: int,
        *,
        rendezvous_timeout_s: float = 300.0,
        rendezvous_poll_interval_s: float = 0.1,
        **pbt_kwargs: Any,
    ) -> None:
        if not _RAY_AVAILABLE:
            raise ModuleNotFoundError(
                'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
            )
        if "hyperparam_mutations" in pbt_kwargs or "custom_explore_fn" in pbt_kwargs:
            raise TypeError(
                "ClanController owns mutation; do not pass Ray PBT exploration policy"
            )
        if pbt_kwargs.get("synch", True) is not True:
            raise ValueError("ClanBasedTraining requires synchronous PBT")
        pbt_kwargs.pop("synch", None)

        time_attr = pbt_kwargs.get("time_attr", "training_iteration")
        if time_attr == "time_total_s":
            raise ValueError(
                "ClanBasedTraining requires a common progress counter, not time_total_s"
            )
        if pbt_kwargs.get("require_attrs", True) is not True:
            raise ValueError(
                "ClanBasedTraining requires require_attrs=True so missing round reports fail"
            )
        pbt_kwargs["time_attr"] = time_attr
        pbt_kwargs["require_attrs"] = True
        pbt_kwargs["log_config"] = False

        self._metadata = _ClanMetadata(
            population_size=population_size,
            rendezvous_timeout_s=rendezvous_timeout_s,
            rendezvous_poll_interval_s=rendezvous_poll_interval_s,
        )
        self._member_ids: set[str] = set()
        self._canonical_resource_signature: object | None = None
        self._rendezvous_handle = None
        self._selection_path: list[dict[str, Any]] = []
        super().__init__(
            synch=True,
            hyperparam_mutations={},
            custom_explore_fn=_identity_config,
            quantile_fraction=0.5,
            **pbt_kwargs,
        )

    @property
    def population_size(self) -> int:
        return self._metadata.population_size

    @property
    def progress_attribute(self) -> str:
        """Return the monotonic progress key used for round boundaries."""

        return self._time_attr

    @property
    def selection_path(self) -> tuple[dict[str, Any], ...]:
        """Return the controller-selected winner record for each completed round."""

        return tuple(dict(item) for item in self._selection_path)

    def on_trial_add(self, tune_controller, trial) -> None:
        self._metadata.bind_trial_config(trial.config)
        super().on_trial_add(tune_controller, trial)

        self._member_ids.add(trial.trial_id)
        if len(self._member_ids) > self.population_size:
            raise RuntimeError("Tune created more trials than ClanBasedTraining.population_size")
        if trial.max_failures != 0:
            raise ValueError(
                "Independent Ray trial recovery is unsupported. Set max_failures=0 "
                "so a failed collective window terminates with the population."
            )

        resource_signature = self._resource_signature(trial)
        if self._canonical_resource_signature is None:
            self._canonical_resource_signature = resource_signature
        elif resource_signature != self._canonical_resource_signature:
            raise ValueError("Every clan trial must request identical resources")

        if len(self._member_ids) == self.population_size:
            self._publish_members()

    def on_trial_result(self, tune_controller, trial, result: dict[str, Any]) -> str:
        if len(self._member_ids) != self.population_size:
            raise RuntimeError(
                "The full clan population was not created before training began. "
                "Set num_samples and max_concurrent_trials to population_size and "
                "ensure the cluster can schedule every member simultaneously."
            )
        self._metadata.bind_trial_config(trial.config)
        if CLAN_ROUND_RESULT_KEY not in result:
            raise RuntimeError("Tune result is missing the Clan round decision record")
        return super().on_trial_result(tune_controller, trial, result)

    def _quantiles(self):
        """Return every loser as a PBT target and the sole winner as its source."""

        reports = []
        for trial, state in self._trial_state.items():
            if trial.is_finished() or state.last_result is None:
                continue
            decision = state.last_result[CLAN_ROUND_RESULT_KEY]
            reports.append((trial, state.last_result, decision))

        if len(reports) != self.population_size:
            return [], []

        round_indices = {int(decision["round_index"]) for _, _, decision in reports}
        winner_ids = {int(decision["winner_id"]) for _, _, decision in reports}
        member_ids = {int(decision["member_id"]) for _, _, decision in reports}
        if len(round_indices) != 1 or len(winner_ids) != 1:
            raise RuntimeError("Clan processes disagreed on the completed round or winner")
        if member_ids != set(range(self.population_size)):
            raise RuntimeError("Tune results do not describe one complete Clan population")

        round_index = round_indices.pop()
        winner_id = winner_ids.pop()
        winner_matches = [
            (trial, result, decision)
            for trial, result, decision in reports
            if int(decision["member_id"]) == winner_id
        ]
        if len(winner_matches) != 1:
            raise RuntimeError("selected Clan winner does not identify exactly one Tune trial")
        winner_trial, winner_result, winner_decision = winner_matches[0]
        if winner_result.get(SHOULD_CHECKPOINT) is not True:
            raise RuntimeError("the controller-selected winner did not report a checkpoint")
        if any(
            result.get(SHOULD_CHECKPOINT) is True and trial is not winner_trial
            for trial, result, _ in reports
        ):
            raise RuntimeError("a losing Clan member reported an unnecessary checkpoint")

        if not self._selection_path or self._selection_path[-1]["round_index"] != round_index:
            self._selection_path.append(
                {
                    "round_index": round_index,
                    "winner_id": winner_id,
                    "trial_id": winner_trial.trial_id,
                    "config": dict(winner_decision["config"]),
                }
            )

        losers = [trial for trial, _, _ in reports if trial is not winner_trial]
        return losers, [winner_trial]

    def _get_new_config(self, trial, trial_to_clone):
        """Preserve target-local construction state while PBT assigns winner state."""

        del trial_to_clone
        config = dict(trial.config)
        self._metadata.bind_trial_config(config)
        return config, {}

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_rendezvous_handle"] = None
        return state

    @staticmethod
    def _resource_signature(trial) -> object:
        request = trial.placement_group_factory
        if request is None:
            raise RuntimeError(
                "Ray did not resolve a resource request before adding the clan trial"
            )
        if len(request.bundles) != 1:
            raise ValueError(
                "Each clan trial must request one resource bundle for one Lightning process"
            )
        bundles = tuple(
            tuple(sorted((key, float(value)) for key, value in bundle.items()))
            for bundle in request.bundles
        )
        return bundles, request.strategy

    def _publish_members(self) -> None:
        from clan_based_tuning.ray.rendezvous import get_or_create_rendezvous

        if self._rendezvous_handle is None:
            self._rendezvous_handle = get_or_create_rendezvous(self._metadata)
        import ray

        ray.get(self._rendezvous_handle.register_members.remote(sorted(self._member_ids)))


def _identity_config(config):
    return config
