"""Lightning callback that closes one Clan generation at validation end.

Each Tune member owns a diverged candidate, so its validation fitness must remain local until
this callback explicitly gathers one scalar from every DDP rank. Every worker then resolves
the same winner, all ranks participate in Lightning checkpoint construction/barriers, only the
winner persists the continuation, and each worker reports enough identity/decision metadata
for the driver scheduler to cross-check the distributed view before propagation.

The callback never interprets or applies the genome. User code still owns optimizer/model
mutation after Lightning restores the selected checkpoint.
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
    """Turn comparable member-local validation results into one Tune generation boundary.

    The callback intentionally computes winner identity on the workers even though the driver
    scheduler computes it again. The worker decision determines which rank may write the
    Lightning checkpoint; the driver's independent decision later verifies that DDP rank
    identity, validation ordering, and selection semantics all agree before that checkpoint is
    inherited.

    Args:
        lightning_metric: Lightning callback-metric name used as fitness. If omitted, the Tune
            metric from the scheduler/runtime is used, keeping one canonical metric name.
        extra_metrics: Optional callback metrics forwarded for observation only. A list keeps
            names unchanged; a mapping renames ``{ray_name: lightning_name}``.
        filename: Name used inside the temporary Tune checkpoint directory. It does not change
            Lightning's checkpoint format.
        _winner_selector: Replacement selection policy for isolated tests. Production must use
            the same deterministic policy as the driver scheduler.

    Notes:
        The fitness metric must remain member-local. Logging it with Lightning ``sync_dist``
        reduction before this callback would erase candidate differences and invalidate parent
        selection.
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
        """Close a real validation boundary; ignore Lightning's pre-training sanity pass.

        The method gathers raw fitnesses in DDP rank order, selects the common winner, scopes
        Lightning's next checkpoint write to that rank, and reports the local result plus
        worker-side decision metadata to Tune. ``try/finally`` around the checkpoint scope is
        critical: an exception must not leave later user checkpoints winner-gated.
        """

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
        """Read a required callback metric without weakening missing-metric failures.

        Lightning callback metrics may be tensors or Python scalars depending on how the user
        logged them. CBT normalizes only the scalar representation; a missing metric remains a
        configuration error rather than acquiring a default fitness.
        """

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
        """Forward only metrics the caller explicitly requested, preserving rename semantics.

        Fitness is intentionally added by ``on_validation_end`` afterward so the scheduler's
        canonical metric cannot be accidentally replaced by an auxiliary mapping.
        """

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
        """Gather one unreduced fitness per DDP rank in the scheduler's stable member order.

        ``ClanDDPStrategy`` makes global rank equal stable member ID, so Lightning's all-gather
        order is directly usable by the shared selection policy. Float64 avoids losing
        comparison detail merely because the training model uses lower-precision arithmetic.
        """

        value = torch.tensor(
            [local_fitness],
            device=trainer.strategy.root_device,
            dtype=torch.float64,
        )
        gathered = trainer.strategy.all_gather(value)
        return [float(item) for item in gathered.detach().reshape(-1).cpu().tolist()]
