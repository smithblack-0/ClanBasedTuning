"""Lightning callbacks for one process-local Clan round transition."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

from lightning import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback

from clan_based_tuning.controller import ClanController
from clan_based_tuning.optimizer import (
    OptimizerStrategy,
    apply_optimizer_strategy as default_optimizer_strategy,
)
from clan_based_tuning.spec import CLAN_ROUND_RESULT_KEY


class ClanControllerRestore(Callback):
    """Checkpoint controller state and reconcile the live optimizer after restore.

    Lightning owns serialization and optimizer restoration. This callback contributes
    the selected controller parent to that checkpoint, advances the receiving local
    controller only after restore, and applies its resulting optimizer configuration.
    """

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

    def continue_selected_local_state(self, trainer: Trainer) -> None:
        """Advance a winner that Tune resumed without reconstructing its actor."""

        self.controller.accept_local_winner_checkpoint()
        self.controller.advance()
        self.apply_current_config(trainer)

    def apply_current_config(self, trainer: Trainer) -> None:
        self._apply_optimizer_strategy(trainer.optimizers, self.controller.get_config())


class ClanTuneReportCallback(Callback):
    """Publish one comparable result and checkpoint only the selected local winner.

    The callback runs inside one Tune trial process at the qualifying Lightning event.
    Controller callbacks exchange plain round records through Ray before this callback
    knows whether the local state won. Only that process asks Lightning to serialize a
    checkpoint. ``tune.report`` then hands both the result and optional checkpoint to
    the synchronous scheduler.
    """

    def __init__(
        self,
        controller: ClanController,
        restore: ClanControllerRestore,
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
        self.restore = restore
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
            trainer.save_checkpoint(os.path.join(checkpoint_dir, self._filename))
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
        report[CLAN_ROUND_RESULT_KEY] = {
            "member_id": self.controller.member_id,
            "round_index": self.controller.round_index,
            "winner_id": winner_id,
            "config": self.controller.get_config(),
        }

        from ray import tune

        with self._winner_checkpoint(trainer, is_winner) as checkpoint:
            tune.report(report, checkpoint=checkpoint)

        # Synchronous Tune normally pauses and reconstructs every process. If it
        # resumes the selected source actor in place, its local model and optimizer
        # are already exactly the checkpointed winner state.
        self.restore.continue_selected_local_state(trainer)
