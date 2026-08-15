"""Lightning callback closing one Clan round through the active DDP context.

At validation end, ``ClanTuneReportCallback`` reads one member-local fitness, gathers one
scalar from every Clan member through Lightning's existing strategy, selects the common
winner, and reports the round to Ray Tune. Every rank participates in Lightning checkpoint
construction/barriers while only the selected member persists and reports the continuation.
Genome interpretation and application remain entirely in user code.
"""

import logging
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence

import torch
from lightning.pytorch import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback
from ray import tune

from clan_based_tuning.evolution import select_winner_id
from clan_based_tuning.lightning_strategy import ClanDDPStrategy
from clan_based_tuning.protocol import (
    CLAN_CHECKPOINT_SOURCE,
    CLAN_MEMBER_ID,
    CLAN_WINNER_ID,
)

_LOGGER = logging.getLogger(__name__)


# Main


class ClanTuneReportCallback(Callback):
    """Resolve one Clan boundary and report it through ordinary Ray Tune.

    Args:
        lightning_metric: Lightning callback-metric name to use as fitness. By default this is
            the same metric configured on ``tune.TuneConfig``.
        extra_metrics: Optional Lightning callback metrics to forward to Ray. A list preserves
            names; a mapping uses ``{ray_name: lightning_name}``.
        filename: File name used inside the temporary Ray checkpoint directory.
        _winner_selector: Injectable population-selection function used by isolated tests.

    Raises:
        TypeError: If used without ``ClanDDPStrategy``.
        RuntimeError: If the required Lightning metric is absent.

    Notes:
        The fitness metric must remain member-local. Do not log it with cross-rank
        ``sync_dist`` reduction before CBT compares diverged candidates.
    """

    def __init__(
        self,
        *,
        lightning_metric: str | None = None,
        extra_metrics: list[str] | dict[str, str] | None = None,
        filename: str = "checkpoint.ckpt",
        _winner_selector: Callable[[Sequence[float], str], int] = select_winner_id,
    ) -> None:
        self._lightning_metric = lightning_metric
        self._extra_metrics = extra_metrics
        self._filename = filename
        self._winner_selector = _winner_selector

    def on_validation_end(self, trainer: Trainer, pl_module: LightningModule) -> None:
        """Gather fitness, checkpoint the selected member, and report one Tune boundary."""

        del pl_module
        if trainer.sanity_checking:
            return
        if not isinstance(trainer.strategy, ClanDDPStrategy):
            raise TypeError("ClanTuneReportCallback requires ClanDDPStrategy")

        runtime = trainer.strategy.clan_runtime
        lightning_metric = self._lightning_metric or runtime.spec.metric
        fitness = self._metric_value(trainer, lightning_metric)
        population = self._exchange_fitness(trainer, fitness)
        winner_id = self._winner_selector(population, runtime.spec.mode)
        is_winner = runtime.member_id == winner_id

        report = self._extra_report(trainer)
        report[runtime.spec.metric] = fitness
        report[CLAN_MEMBER_ID] = runtime.member_id
        report[CLAN_WINNER_ID] = winner_id
        report[CLAN_CHECKPOINT_SOURCE] = is_winner

        _LOGGER.debug(
            "Clan member resolved boundary member=%d winner=%d fitness=%s population=%s",
            runtime.member_id,
            winner_id,
            fitness,
            population,
        )
        with tempfile.TemporaryDirectory() as checkpoint_dir:
            checkpoint_path = os.path.join(checkpoint_dir, self._filename)
            trainer.strategy.begin_round_checkpoint(winner_id)
            try:
                trainer.save_checkpoint(checkpoint_path)
            finally:
                trainer.strategy.end_round_checkpoint()

            checkpoint = tune.Checkpoint.from_directory(checkpoint_dir) if is_winner else None
            if is_winner:
                _LOGGER.info(
                    "Clan checkpoint source selected member=%d fitness=%s",
                    runtime.member_id,
                    fitness,
                )
            tune.report(report, checkpoint=checkpoint)

    @staticmethod
    def _metric_value(trainer: Trainer, metric: str) -> float:
        """Read one required callback metric and normalize tensor/scalar values to float."""

        try:
            value = trainer.callback_metrics[metric]
        except KeyError as error:
            raise RuntimeError(
                f"Lightning did not report required Clan metric {metric!r}"
            ) from error
        if hasattr(value, "item"):
            value = value.item()
        return float(value)

    def _extra_report(self, trainer: Trainer) -> dict[str, float]:
        """Return explicitly requested auxiliary Lightning metrics under their Ray names."""

        metrics = self._extra_metrics
        if metrics is None:
            return {}

        report: dict[str, float] = {}
        if isinstance(metrics, Mapping):
            for report_name, lightning_name in metrics.items():
                report[report_name] = self._metric_value(trainer, lightning_name)
            return report

        for name in metrics:
            report[name] = self._metric_value(trainer, name)
        return report

    @staticmethod
    def _exchange_fitness(trainer: Trainer, local_fitness: float) -> list[float]:
        """Gather one scalar per member through Lightning's active DDP strategy."""

        value = torch.tensor(
            [local_fitness],
            device=trainer.strategy.root_device,
            dtype=torch.float64,
        )
        gathered = trainer.strategy.all_gather(value)
        return [float(item) for item in gathered.detach().reshape(-1).cpu().tolist()]
