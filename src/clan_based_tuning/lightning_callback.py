"""Lightning callback closing one Clan round through the established DDP context."""

from __future__ import annotations

import json
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
    CLAN_GENOME_JSON,
    CLAN_MEMBER_ID,
    CLAN_METADATA_KEY,
    CLAN_SCHEMA_VERSION,
    CLAN_WINNER_ID,
)
from clan_based_tuning.runtime import current_runtime


class ClanTuneReportCallback(Callback):
    """Compare local fitness, persist one winner, and report the round to Tune.

    Genome use is outside this callback. It observes the local Lightning metric at
    validation end, exchanges only that scalar through the already-established DDP
    process group, and asks ``ClanController`` which member is the checkpoint source.

    Every rank then enters Lightning's ordinary checkpoint construction and barrier. The
    accompanying ``ClanDDPStrategy`` writes the checkpoint only on the selected rank, so
    permanent checkpoint storage remains one continuation per Clan round rather than one
    checkpoint per member.
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

        runtime = current_runtime()
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
        report[CLAN_GENOME_JSON] = json.dumps(
            runtime.controlled_genome,
            sort_keys=True,
            separators=(",", ":"),
        )
        report[CLAN_CHECKPOINT_SOURCE] = is_winner

        from ray import tune

        with tempfile.TemporaryDirectory() as checkpoint_dir:
            checkpoint_path = os.path.join(checkpoint_dir, self._filename)
            trainer.strategy.begin_round_checkpoint(winner_id)
            try:
                trainer.save_checkpoint(checkpoint_path)
            finally:
                trainer.strategy.end_round_checkpoint()

            checkpoint = None
            if is_winner:
                checkpoint = tune.Checkpoint.from_directory(checkpoint_dir)
                checkpoint.update_metadata(
                    {
                        CLAN_METADATA_KEY: {
                            "schema_version": CLAN_SCHEMA_VERSION,
                            "member_id": runtime.member_id,
                            "genome": runtime.controlled_genome,
                        }
                    }
                )
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
        """Gather one scalar per member over Lightning's active process group."""

        if not torch.distributed.is_available() or not torch.distributed.is_initialized():
            raise RuntimeError("Clan fitness exchange requires Lightning's active DDP group")

        value = torch.tensor(
            local_fitness,
            device=trainer.strategy.root_device,
            dtype=torch.float64,
        )
        gathered = [torch.empty_like(value) for _ in range(trainer.strategy.world_size)]
        torch.distributed.all_gather(gathered, value)
        return [float(item.item()) for item in gathered]
