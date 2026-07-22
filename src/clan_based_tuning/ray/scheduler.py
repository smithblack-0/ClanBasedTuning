"""Synchronous Ray PBT scheduler for shared-gradient native trials."""

from __future__ import annotations

from typing import Any

from clan_based_tuning.spec import CLAN_METADATA_KEY, _ClanMetadata

try:
    from ray.tune.schedulers import PopulationBasedTraining
except ModuleNotFoundError:
    PopulationBasedTraining = object  # type: ignore[assignment,misc]
    _RAY_AVAILABLE = False
else:
    _RAY_AVAILABLE = True


class ClanBasedTraining(PopulationBasedTraining):  # type: ignore[misc]
    """Run ordinary Ray PBT while keeping one complete gradient-sharing clan.

    Ray remains authoritative for trial identity, scoring, mutation, checkpoint
    selection and cloning, pause, resume, and scheduler persistence. This class
    adds only the constraints and rendezvous lifecycle required for every native
    trial to enter the same synchronous DDP window.
    """

    _supports_buffered_results = False

    def __init__(
        self,
        population_size: int,
        *,
        synch: bool = True,
        rendezvous_timeout_s: float = 300.0,
        rendezvous_poll_interval_s: float = 0.1,
        **pbt_kwargs: Any,
    ) -> None:
        if not _RAY_AVAILABLE:
            raise ModuleNotFoundError(
                'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
            )
        if not synch:
            raise ValueError("ClanBasedTraining requires synchronous PBT")

        time_attr = pbt_kwargs.get("time_attr", "training_iteration")
        if time_attr == "time_total_s":
            raise ValueError(
                "ClanBasedTraining requires a common progress counter, not time_total_s"
            )
        if pbt_kwargs.get("require_attrs", True) is not True:
            raise ValueError(
                "ClanBasedTraining requires require_attrs=True so missing fitness or "
                "progress reports fail immediately"
            )
        pbt_kwargs["time_attr"] = time_attr
        pbt_kwargs["require_attrs"] = True
        mutations = pbt_kwargs.get("hyperparam_mutations", {})
        if CLAN_METADATA_KEY in mutations:
            raise ValueError(f"{CLAN_METADATA_KEY!r} is reserved integration metadata")

        self._metadata = _ClanMetadata(
            population_size=population_size,
            rendezvous_timeout_s=rendezvous_timeout_s,
            rendezvous_poll_interval_s=rendezvous_poll_interval_s,
        )
        self._member_ids: set[str] = set()
        self._canonical_resource_signature: object | None = None
        self._rendezvous_handle = None
        super().__init__(synch=True, **pbt_kwargs)

    @property
    def population_size(self) -> int:
        return self._metadata.population_size

    @property
    def progress_attribute(self) -> str:
        """Return the monotonic progress key used for perturbation boundaries."""

        return self._time_attr

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
        return super().on_trial_result(tune_controller, trial, result)

    def _get_new_config(self, trial, trial_to_clone):
        """Use native Ray exploration while protecting rendezvous authority."""

        config, operations = super()._get_new_config(trial, trial_to_clone)
        self._metadata.bind_trial_config(config)
        return config, operations

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
