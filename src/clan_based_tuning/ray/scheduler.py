"""Strict synchronous Ray PBT scheduler for shared-gradient native trials."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from clan_based_tuning.spec import ClanSpec

try:
    from ray.tune.schedulers import PopulationBasedTraining
except ModuleNotFoundError:
    PopulationBasedTraining = object  # type: ignore[assignment,misc]
    _RAY_AVAILABLE = False
else:
    _RAY_AVAILABLE = True


class ClanBasedTraining(PopulationBasedTraining):  # type: ignore[misc]
    """Constrain Ray PBT to one fixed synchronous shared-gradient clan.

    Ray's scheduler remains authoritative for trial identity, checkpoint-driven
    exploitation, configuration mutation, pause, and resume. This subclass adds
    only the constraints required for all native trials to participate in one
    collective training window.
    """

    _supports_buffered_results = False

    def __init__(
        self,
        clan: ClanSpec,
        *,
        hyperparam_mutations: dict[str, Any],
        synch: bool = True,
        custom_explore_fn: Any | None = None,
        **kwargs: Any,
    ) -> None:
        if not _RAY_AVAILABLE:
            raise ModuleNotFoundError(
                'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
            )
        if not synch:
            raise ValueError("ClanBasedTraining requires synchronous PBT")
        if custom_explore_fn is not None:
            raise ValueError(
                "custom_explore_fn is unsupported because it could mutate "
                "non-optimizer trial configuration"
            )
        mutation_keys = frozenset(hyperparam_mutations)
        if mutation_keys != clan.optimizer_config_keys:
            raise ValueError(
                "hyperparam_mutations must exactly match the optimizer fields "
                f"declared by ClanSpec: expected {sorted(clan.optimizer_config_keys)}, "
                f"got {sorted(mutation_keys)}"
            )
        if any(isinstance(value, dict) for value in hyperparam_mutations.values()):
            raise ValueError(
                "Nested PBT mutation dictionaries are not supported in the first release"
            )

        time_attr = kwargs.get("time_attr", "training_iteration")
        if time_attr == "time_total_s":
            raise ValueError(
                "ClanBasedTraining requires a common progress counter, not wall-clock time_total_s"
            )
        if kwargs.get("require_attrs", True) is not True:
            raise ValueError(
                "ClanBasedTraining requires require_attrs=True so missing fitness or "
                "progress reports fail immediately"
            )
        kwargs["time_attr"] = time_attr
        kwargs["require_attrs"] = True

        self.clan = clan
        self._member_ranks: dict[str, int] = {}
        self._canonical_static_config_signature: bytes | None = None
        self._canonical_resource_signature: object | None = None
        self._rendezvous_handle = None

        super().__init__(
            hyperparam_mutations=hyperparam_mutations,
            custom_explore_fn=None,
            synch=True,
            **kwargs,
        )

    @property
    def progress_attribute(self) -> str:
        """Return the common monotonic progress key used for perturbation boundaries."""

        return self._time_attr

    def on_trial_add(self, tune_controller, trial) -> None:
        self._resolve_or_bind_clan(trial.config)
        super().on_trial_add(tune_controller, trial)
        trial_id = trial.trial_id
        if trial_id not in self._member_ranks:
            if len(self._member_ranks) >= self.clan.population_size:
                raise RuntimeError("Tune created more trials than ClanSpec.population_size")
            self._member_ranks[trial_id] = len(self._member_ranks)

        static_signature = self._static_config_signature(trial.config)
        if self._canonical_static_config_signature is None:
            self._canonical_static_config_signature = static_signature
        elif static_signature != self._canonical_static_config_signature:
            raise ValueError(
                "Clan trials may differ only in declared optimizer hyperparameters"
            )

        if trial.max_failures != 0:
            raise ValueError(
                "Independent Ray trial recovery is unsupported. Set max_failures=0 "
                "so a failed collective window terminates instead of restoring one member alone."
            )

        resource_signature = self._resource_signature(trial)
        if self._canonical_resource_signature is None:
            self._canonical_resource_signature = resource_signature
        elif resource_signature != self._canonical_resource_signature:
            raise ValueError("Every clan trial must request identical resources")

        self._publish_member_ranks()

    def on_trial_result(self, tune_controller, trial, result: dict[str, Any]) -> str:
        if len(self._member_ranks) != self.clan.population_size:
            raise RuntimeError(
                "The full clan population was not created before training began"
            )
        if self._static_config_signature(trial.config) != self._canonical_static_config_signature:
            raise RuntimeError(
                "A clan trial changed non-optimizer configuration during training"
            )
        return super().on_trial_result(tune_controller, trial, result)

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_rendezvous_handle"] = None
        return state

    def _resolve_or_bind_clan(self, config: dict[str, Any]) -> None:
        resolved = self.clan.resolve_trial_config(config)
        if self._member_ranks:
            if resolved != self.clan:
                raise RuntimeError("Tune trials contain inconsistent clan metadata")
        else:
            self.clan = resolved
        self.clan.bind_trial_config(config)

    def _static_config_signature(self, config: dict[str, Any]) -> bytes:
        import ray.cloudpickle as cloudpickle

        static_config = {
            key: value
            for key, value in config.items()
            if key not in self.clan.optimizer_config_keys
        }
        return sha256(cloudpickle.dumps(static_config)).digest()

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

    def _publish_member_ranks(self) -> None:
        from clan_based_tuning.ray.rendezvous import get_or_create_rendezvous

        if self._rendezvous_handle is None:
            self._rendezvous_handle = get_or_create_rendezvous(self.clan)
        import ray

        ray.get(self._rendezvous_handle.register_members.remote(dict(self._member_ranks)))
