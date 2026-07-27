"""Synchronous Ray PBT scheduler for explicitly identified Clan members."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from clan_based_tuning.spec import (
    CLAN_MEMBER_ID_KEY,
    CLAN_METADATA_KEY,
    _ClanMetadata,
)

try:
    from ray.tune.schedulers import PopulationBasedTraining
except ModuleNotFoundError:
    PopulationBasedTraining = object  # type: ignore[assignment,misc]
    _RAY_AVAILABLE = False
else:
    _RAY_AVAILABLE = True


class ClanBasedTraining(PopulationBasedTraining):  # type: ignore[misc]
    """Run synchronous PBT over one explicitly identified Clan population.

    Every Tune trial config must contain one stable integer ``clan_member_id``.
    The scheduler validates that the live trial set contains exactly one trial for
    each member ID and preserves the target member's ID when native PBT clones a
    source configuration. It does not infer logical Clan identity from Tune trial
    creation order or trial IDs.

    The existing proof-of-concept rendezvous metadata remains separate. Explicit
    Clan member identity does not configure DDP ranks or process-group topology.
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
        reserved = {CLAN_MEMBER_ID_KEY, CLAN_METADATA_KEY}.intersection(mutations)
        if reserved:
            names = ", ".join(sorted(repr(name) for name in reserved))
            raise ValueError(f"Reserved integration keys may not be mutated: {names}")

        self._metadata = _ClanMetadata(
            population_size=population_size,
            rendezvous_timeout_s=rendezvous_timeout_s,
            rendezvous_poll_interval_s=rendezvous_poll_interval_s,
        )
        self._member_id_by_trial: dict[str, int] = {}
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
        member_id = self._member_id_from_config(trial.config)
        self._validate_new_trial(trial, member_id)
        resource_signature = self._resource_signature(trial)
        if (
            self._canonical_resource_signature is not None
            and resource_signature != self._canonical_resource_signature
        ):
            raise ValueError("Every clan trial must request identical resources")

        self._metadata.bind_trial_config(trial.config)
        super().on_trial_add(tune_controller, trial)
        self._member_id_by_trial[trial.trial_id] = member_id
        if self._canonical_resource_signature is None:
            self._canonical_resource_signature = resource_signature
        if len(self._member_id_by_trial) == self.population_size:
            self._publish_members()

    def on_trial_result(self, tune_controller, trial, result: dict[str, Any]) -> str:
        expected_ids = set(range(self.population_size))
        if set(self._member_id_by_trial.values()) != expected_ids:
            raise RuntimeError(
                "The full explicitly identified Clan population was not created before "
                "training began"
            )
        self._metadata.bind_trial_config(trial.config)
        member_id = self._member_id_from_config(trial.config)
        try:
            registered_member_id = self._member_id_by_trial[trial.trial_id]
        except KeyError as error:
            raise RuntimeError(
                "Tune reported a result for an unregistered Clan trial"
            ) from error
        if member_id != registered_member_id:
            raise RuntimeError(
                "A Tune trial changed its Clan member ID after registration"
            )
        return super().on_trial_result(tune_controller, trial, result)

    def _get_new_config(self, trial, trial_to_clone):
        """Preserve target-local member identity across native PBT cloning."""

        config, operations = super()._get_new_config(trial, trial_to_clone)
        try:
            member_id = self._member_id_by_trial[trial.trial_id]
        except KeyError as error:
            raise RuntimeError(
                "PBT attempted to configure an unregistered Clan trial"
            ) from error
        config[CLAN_MEMBER_ID_KEY] = member_id
        self._metadata.bind_trial_config(config)
        return config, operations

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_rendezvous_handle"] = None
        return state

    def _member_id_from_config(self, config: Mapping[str, Any]) -> int:
        try:
            member_id = config[CLAN_MEMBER_ID_KEY]
        except KeyError as error:
            raise RuntimeError(
                f"Every Clan trial config must define {CLAN_MEMBER_ID_KEY!r}"
            ) from error
        if isinstance(member_id, bool) or not isinstance(member_id, int):
            raise TypeError(f"{CLAN_MEMBER_ID_KEY!r} must be an integer")
        if not 0 <= member_id < self.population_size:
            raise ValueError(
                f"{CLAN_MEMBER_ID_KEY!r} must be between 0 and "
                f"{self.population_size - 1}"
            )
        return member_id

    def _validate_new_trial(self, trial, member_id: int) -> None:
        if trial.trial_id in self._member_id_by_trial:
            raise RuntimeError(f"Tune added Clan trial {trial.trial_id!r} more than once")
        if member_id in self._member_id_by_trial.values():
            raise RuntimeError(
                f"Clan member ID {member_id} was assigned to more than one trial"
            )
        if len(self._member_id_by_trial) == self.population_size:
            raise RuntimeError(
                "Tune created more trials than ClanBasedTraining.population_size"
            )
        if trial.max_failures != 0:
            raise ValueError(
                "Independent Ray trial recovery is unsupported. Set max_failures=0 "
                "so a failed collective window terminates with the population."
            )

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

        trial_ids = [
            trial_id
            for trial_id, _ in sorted(
                self._member_id_by_trial.items(), key=lambda item: item[1]
            )
        ]
        ray.get(self._rendezvous_handle.register_members.remote(trial_ids))
