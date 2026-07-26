"""Lightning callbacks for one process-local Clan round transition."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

from lightning import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback

from clan_based_tuning.controller import ClanController
from clan_based_tuning.lightning.checkpoint import save_local_checkpoint
from clan_based_tuning.optimizer import OptimizerStrategy
from clan_based_tuning.optimizer import (
    apply_optimizer_strategy as default_optimizer_strategy,
)
from clan_based_tuning.spec import (
    CLAN_CONFIG_KEY,
    CLAN_MEMBER_ID_KEY,
    CLAN_ROUND_INDEX_KEY,
    CLAN_WINNER_ID_KEY,
)


class ClanControllerRestore(Callback):
    """Checkpoint controller state and reconcile the live optimizer after restore."""

    def __init__(
        self,
        controller: ClanController,
        apply_optimizer_strategy: OptimizerStrategy = default_optimizer_strategy,
    ) -> None:
        self.controller = controller
        self._apply_optimizer_strategy = apply_optimizer_strategy
        self._loaded_winner = False

    def state_dict(self) -> dict[str, Any]:
        return {"controller": self.controller.state_dict()}

    def load_state_dict(self, state_dict: dict[str, Any]) -> None:
        self.controller.load_state_dict(state_dict["controller"])
        self._loaded_winner = True

    def on_train_start(self, trainer: Trainer, pl_module: LightningModule) -> None:
        del pl_module
        if self._loaded_winner:
            self.controller.advance()
            self._loaded_winner = False
        self.apply_current_config(trainer)

    def apply_current_config(self, trainer: Trainer) -> None:
        self._apply_optimizer_strategy(trainer.optimizers, self.controller.get_config())


class ClanTuneReportCallback(Callback):
    """Report a comparable result and checkpoint only the selected local winner."""

    def __init__(
        self,
        controller: ClanController,
        *,
        metrics: str | list[str] | dict[str, str],
        fitness_metric: str,
        filename: str = "checkpoint",
        on: str = "validation_end",
    ) -> None:
        super().__init__()
        if isinstance(metrics, str):
            metrics = [metrics]
        self.controller = controller
        self._metrics = metrics
        self._fitness_metric = fitness_metric
        self._filename = filename
        hook_name = f"on_{on}"
        if not hasattr(self, hook_name):
            raise ValueError(f"unknown Lightning callback hook: {on!r}")
        setattr(self, hook_name, self._handle)

    def _report_dict(self, trainer: Trainer) -> dict[str, Any]:
        report: dict[str, Any] = {}
        keys = self._metrics.keys() if isinstance(self._metrics, Mapping) else self._metrics
        for key in keys:
            metric = self._metrics[key] if isinstance(self._metrics, Mapping) else key
            value = trainer.callback_metrics[metric]
            report[key] = float(value.item() if hasattr(value, "item") else value)
        return report

    @contextmanager
    def _winner_checkpoint(self, trainer: Trainer, is_winner: bool):
        if not is_winner:
            yield None
            return
        from ray.train import Checkpoint

        with tempfile.TemporaryDirectory() as checkpoint_dir:
            save_local_checkpoint(trainer, os.path.join(checkpoint_dir, self._filename))
            yield Checkpoint.from_directory(checkpoint_dir)

    def _handle(self, trainer: Trainer, pl_module: LightningModule) -> None:
        del pl_module
        if trainer.sanity_checking:
            return

        report = self._report_dict(trainer)
        self.controller.set_fitness(report[self._fitness_metric])
        is_winner = self.controller.is_round_winner()
        winner_id = self.controller.winner_id
        if winner_id is None:
            raise RuntimeError("controller did not resolve a winner")
        report.update(
            {
                CLAN_MEMBER_ID_KEY: self.controller.member_id,
                CLAN_ROUND_INDEX_KEY: self.controller.round_index,
                CLAN_WINNER_ID_KEY: winner_id,
                CLAN_CONFIG_KEY: json.dumps(
                    self.controller.get_config(), sort_keys=True, separators=(",", ":")
                ),
            }
        )

        from ray import tune

        with self._winner_checkpoint(trainer, is_winner) as checkpoint:
            tune.report(report, checkpoint=checkpoint)
