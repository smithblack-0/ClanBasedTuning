"""Legacy proof-of-concept Lightning assembly helpers.

Milestone 3's accepted path is explicit composition of ``ClanTuneSession``,
``ClanController``, the Lightning callbacks, environment, and strategy. These helpers
remain only as prior construction evidence until the usability milestone replaces or
removes them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lightning import Trainer
from lightning.pytorch.callbacks import EarlyStopping

from clan_based_tuning.lightning.environment import (
    ClanLightningEnvironment,
    _ClanRuntime,
)
from clan_based_tuning.lightning.strategy import ClanDDPStrategy
from clan_based_tuning.optimizer import OptimizerStrategy
from clan_based_tuning.optimizer import (
    apply_optimizer_strategy as default_optimizer_strategy,
)
from clan_based_tuning.spec import _ClanMetadata, _metadata_from_trial_config

if TYPE_CHECKING:
    from lightning.pytorch.callbacks import Callback


@dataclass(frozen=True, slots=True)
class ClanLightningPlugins:
    """Concrete objects produced by the legacy proof-of-concept factory."""

    strategy: ClanDDPStrategy
    environment: ClanLightningEnvironment
    report_callback: Callback


def make_clan_lightning_plugins(
    config: Mapping[str, Any],
    *,
    metrics: str | list[str] | dict[str, str],
    apply_optimizer_strategy: OptimizerStrategy = default_optimizer_strategy,
    filename: str = "checkpoint",
    on: str = "validation_end",
    **ddp_kwargs: Any,
) -> ClanLightningPlugins:
    """Return the former all-member-checkpoint proof-of-concept components.

    This helper does not implement the controller-selected winner lifecycle and is not
    the Milestone 3 manual path. ``apply_optimizer_strategy`` is retained only for
    source compatibility and is deliberately not installed into ``ClanDDPStrategy``.
    """

    metadata = _metadata_from_trial_config(config)
    runtime = _resolve_tune_runtime(metadata)
    if not callable(apply_optimizer_strategy):
        raise TypeError("apply_optimizer_strategy must be callable")
    environment = ClanLightningEnvironment(runtime)
    strategy = ClanDDPStrategy(runtime, **ddp_kwargs)
    callback = _tune_report_callback(metrics=metrics, filename=filename, on=on)
    return ClanLightningPlugins(
        strategy=strategy,
        environment=environment,
        report_callback=callback,
    )


def prepare_clan_trainer(trainer: Trainer) -> Trainer:
    """Validate the legacy proof-of-concept composition and return it unchanged."""

    if not isinstance(trainer.strategy, ClanDDPStrategy):
        raise TypeError("Trainer.strategy must be ClanDDPStrategy")
    if not isinstance(trainer.strategy.cluster_environment, ClanLightningEnvironment):
        raise TypeError(
            "Trainer.plugins must include the ClanLightningEnvironment returned by "
            "make_clan_lightning_plugins()"
        )
    if trainer.num_devices != 1 or trainer.num_nodes != 1:
        raise ValueError("Clan Based Training requires one Lightning device/process per Tune trial")
    callback_type = _tune_report_callback_type()
    if not any(isinstance(callback, callback_type) for callback in trainer.callbacks):
        raise TypeError(
            "Trainer.callbacks must include the Tune reporting callback returned by "
            "make_clan_lightning_plugins()"
        )
    if any(isinstance(callback, EarlyStopping) for callback in trainer.callbacks):
        raise ValueError(
            "Lightning EarlyStopping can terminate one clan member while peers are "
            "inside a collective; stop the population through Ray Tune instead"
        )
    return trainer


def _resolve_tune_runtime(metadata: _ClanMetadata) -> _ClanRuntime:
    try:
        from clan_based_tuning.ray.rendezvous import resolve_tune_runtime
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
        ) from error
    return resolve_tune_runtime(metadata)


def _tune_report_callback(*, metrics, filename: str, on: str):
    callback_type = _tune_report_callback_type()
    return callback_type(metrics=metrics, filename=filename, on=on)


def _tune_report_callback_type():
    try:
        from ray.tune.integration.pytorch_lightning import TuneReportCheckpointCallback
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
        ) from error
    return TuneReportCheckpointCallback
