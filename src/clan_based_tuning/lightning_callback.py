"""Lightning callback closing one Clan round through the established DDP context."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping

import torch
from lightning.pytorch import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback

from clan_based_tuning.controller import ClanController
from clan_based_tuning.lightning_strategy import ClanDDPStrategy
from clan_based_tuning.protocol import (
    CLAN_CHECKPOINT_SOURCE,
    CLAN_MEMBER_ID,
    CLAN_WINNER_ID,
)


class ClanTuneReportCallback(Callback):
    """Resolve a Clan boundary and report it through ordinary Ray Tune.

    The callback reads one member-local Lightning metric, exchanges fitness through the
    active ``ClanDDPStrategy``, selects the common winner, has every rank participate in
    Lightning checkpoint construction, and reports one Ray checkpoint from the selected
    member only. It has no genome-application behavior.

    Args:
        lightning_metric: Lightning callback-metric name to use as fitness. By default this
            is the same metric configured on ``tune.TuneConfig``.
        extra_metrics: Optional Lightning callback metrics to forward to Ray. A list keeps
            the same names; a mapping uses ``{ray_name: lightning_name}``.
        filename: File name used inside the temporary Ray checkpoint directory.

    Raises:
        TypeError: If used without ``ClanDDPStrategy``.
        RuntimeError: If the required Lightning metric is absent.

    Notes:
        The fitness metric must remain member-local. Do not log it with cross-rank
        ``sync_dist`` reduction before CBT compares the diverged candidates.
    """

    def __init__(
        self,
        *,
        lightning_metric: str | None = None,
        extra_metrics: list[str] | dict[str, str] | None = None,
        filename: str = "checkpoint.ckpt",
    ) -> None:
        self._lightning_metric = lightning_metric
        self._extra_metrics = extra_metrics
        self._filename = filename

    def on_validation_end(self, trainer: Trainer, pl_module: LightningModule) -> None:
        del pl_module
        if trainer.sanity_checking:
            return
        if not isinstance(trainer.strategy, ClanDDPStrategy):
            raise TypeError("ClanTuneReportCallback requires ClanDDPStrategy")

        runtime = trainer.strategy.clan_runtime
        lightning_metric = self._lightning_metric or runtime.spec.metric
        fitness = self._metric_value(trainer, lightning_metric)

        controller = ClanController(
            member_id=runtime.member_id,
            population_size=runtime.world_size,
            mode=runtime.spec.mode,
            exchange_fitness=lambda local_fitness: self._exchange_fitness(trainer, local_fitness),
        )
        controller.set_fitness(fitness)
        is_winner = controller.should_save_checkpoint()
        winner_id = controller.winner_id

        report = self._extra_report(trainer)
        report[runtime.spec.metric] = fitness
        report[CLAN_MEMBER_ID] = runtime.member_id
        report[CLAN_WINNER_ID] = winner_id
        report[CLAN_CHECKPOINT_SOURCE] = is_winner

        from ray import tune

        with tempfile.TemporaryDirectory() as checkpoint_dir:
            checkpoint_path = os.path.join(checkpoint_dir, self._filename)
            trainer.strategy.begin_round_checkpoint(winner_id)
            try:
                trainer.save_checkpoint(checkpoint_path)
            finally:
                trainer.strategy.end_round_checkpoint()

            checkpoint = tune.Checkpoint.from_directory(checkpoint_dir) if is_winner else None
            tune.report(report, checkpoint=checkpoint)

    @staticmethod
    def _metric_value(trainer: Trainer, metric: str) -> float:
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
        """Gather one scalar per member through Lightning's active strategy."""

        value = torch.tensor(
            [local_fitness],
            device=trainer.strategy.root_device,
            dtype=torch.float64,
        )
        gathered = trainer.strategy.all_gather(value)
        return [float(item) for item in gathered.detach().reshape(-1).cpu().tolist()]
