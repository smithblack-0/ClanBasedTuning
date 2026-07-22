"""Small construction facade that keeps scheduler and strategy contracts aligned."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from clan_based_tuning.lightning import ClanDDPStrategy, ClanRuntime
from clan_based_tuning.spec import ClanSpec


@dataclass(frozen=True, slots=True)
class ClanBase:
    """Construct matching Ray and Lightning integration objects.

    This is configuration glue, not another controller. Mutable lifecycle state
    remains in Ray's scheduler and the running Lightning strategy instances.
    """

    spec: ClanSpec

    def strategy(
        self,
        trial_config: Mapping[str, Any],
        *,
        runtime: ClanRuntime | None = None,
        **ddp_kwargs: Any,
    ) -> ClanDDPStrategy:
        return ClanDDPStrategy(
            self.spec,
            trial_config,
            runtime=runtime,
            **ddp_kwargs,
        )

    def scheduler(self, **kwargs: Any):
        from clan_based_tuning.ray import ClanBasedTraining

        return ClanBasedTraining(self.spec, **kwargs)

    @property
    def trainer_requirements(self) -> dict[str, Any]:
        """Return required Trainer settings not owned by the strategy object."""

        return {
            "devices": 1,
            "num_nodes": 1,
            "enable_checkpointing": False,
        }

    def tune_config(self, *, scheduler: Any, **kwargs: Any):
        """Create a TuneConfig that keeps the complete clan concurrently resident."""

        try:
            from ray import tune
            from clan_based_tuning.ray import ClanBasedTraining
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
            ) from error

        if not isinstance(scheduler, ClanBasedTraining):
            raise TypeError("scheduler must be created by ClanBase.scheduler()")
        if scheduler.clan.compatibility_signature != self.spec.compatibility_signature:
            raise ValueError("scheduler was created for a different clan structure")

        num_samples = kwargs.pop("num_samples", self.spec.population_size)
        max_concurrent = kwargs.pop(
            "max_concurrent_trials", self.spec.population_size
        )
        reuse_actors = kwargs.pop("reuse_actors", False)
        search_algorithm = kwargs.get("search_alg")
        time_budget = kwargs.get("time_budget_s")
        if num_samples != self.spec.population_size:
            raise ValueError("num_samples must equal ClanSpec.population_size")
        if max_concurrent != self.spec.population_size:
            raise ValueError(
                "max_concurrent_trials must equal ClanSpec.population_size"
            )
        if reuse_actors:
            raise ValueError(
                "Actor reuse is unsupported because each PBT window must rebuild "
                "its cross-trial process group from the selected checkpoints"
            )
        if search_algorithm is not None:
            raise ValueError(
                "A separate Ray search algorithm is unsupported. ClanBasedTraining "
                "owns optimizer exploration through synchronous PBT."
            )
        if time_budget is not None:
            raise ValueError(
                "time_budget_s can interrupt a coupled clan mid-window; stop the run "
                "through the shared progress attribute instead."
            )
        return tune.TuneConfig(
            scheduler=scheduler,
            num_samples=num_samples,
            max_concurrent_trials=max_concurrent,
            reuse_actors=False,
            **kwargs,
        )

    def run_config(self, *, scheduler: Any, **kwargs: Any):
        """Create a RunConfig that stops and fails the clan as one coupled unit."""

        try:
            from ray import tune
            from clan_based_tuning.ray import ClanBasedTraining
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
            ) from error

        if not isinstance(scheduler, ClanBasedTraining):
            raise TypeError("scheduler must be created by ClanBase.scheduler()")
        if scheduler.clan.compatibility_signature != self.spec.compatibility_signature:
            raise ValueError("scheduler was created for a different clan structure")

        stop = kwargs.get("stop")
        if not isinstance(stop, Mapping) or set(stop) != {scheduler.progress_attribute}:
            raise ValueError(
                "stop must be a mapping with exactly the scheduler's common progress "
                f"attribute {scheduler.progress_attribute!r}; per-trial fitness or "
                "callable stoppers can break the collective."
            )

        checkpoint_config = kwargs.get("checkpoint_config")
        if checkpoint_config is not None:
            num_to_keep = checkpoint_config.num_to_keep
            if num_to_keep is not None and num_to_keep <= 2:
                raise ValueError(
                    "Ray PBT may still need a source checkpoint during exploit; "
                    "checkpoint_config.num_to_keep must be None or greater than 2."
                )

        failure_config = kwargs.pop("failure_config", None)
        if failure_config is None:
            failure_config = tune.FailureConfig(max_failures=0, fail_fast=True)
        elif failure_config.max_failures != 0 or not failure_config.fail_fast:
            raise ValueError(
                "Clan Based Training currently requires max_failures=0 and "
                "fail_fast=True; independent member recovery cannot repair a failed "
                "collective window."
            )
        return tune.RunConfig(failure_config=failure_config, **kwargs)

    def tune_checkpoint_path(self, filename: str = "checkpoint"):
        """Materialize the current Ray checkpoint for a Lightning fit call."""

        from clan_based_tuning.ray.checkpoint import tune_checkpoint_path

        return tune_checkpoint_path(filename)

    def tune_report_callback(
        self,
        *,
        metrics: Any,
        filename: str = "checkpoint",
        on: str = "validation_end",
    ):
        """Construct Ray's native Lightning reporting/checkpoint callback."""

        try:
            from ray.tune.integration.pytorch_lightning import (
                TuneReportCheckpointCallback,
            )
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
            ) from error
        return TuneReportCheckpointCallback(
            metrics=metrics,
            filename=filename,
            on=on,
        )
