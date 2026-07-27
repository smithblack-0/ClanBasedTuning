"""Lightning checkpoint and optimizer reconciliation for a Clan transition."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from lightning import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback
from torch.optim import Optimizer

from clan_based_tuning.controller import ClanController
from clan_based_tuning.member_state import CONTROLLER_STATE, OPTIMIZER_CONFIG

__all__ = [
    "MemberStateRestore",
    "OptimizerConfigApplicator",
    "apply_optimizer_config",
    "save_local_checkpoint",
]

OptimizerConfigApplicator = Callable[
    [Sequence[Optimizer], Mapping[str, float]],
    None,
]


def apply_optimizer_config(
    optimizers: Sequence[Optimizer],
    config: Mapping[str, float],
) -> None:
    """Apply scalar Clan values to one optimizer parameter group."""

    if len(optimizers) != 1:
        raise ValueError("the default applicator requires one optimizer; inject another applicator")
    optimizer = optimizers[0]
    if len(optimizer.param_groups) != 1:
        raise ValueError(
            "the default applicator requires one parameter group; inject another applicator"
        )

    group = optimizer.param_groups[0]
    for name, value in config.items():
        if name == "params" or name not in group:
            raise KeyError(f"optimizer parameter group has no configurable {name!r} field")
        group[name] = value


class MemberStateRestore(Callback):
    """Restore member-local policy state after Lightning restores inherited state."""

    def __init__(
        self,
        *,
        controller: ClanController,
        next_member_state: Mapping[str, Any] | None,
        apply_config: OptimizerConfigApplicator = apply_optimizer_config,
    ):
        self._controller = controller
        self._next_member_state = copy.deepcopy(next_member_state)
        self._apply_config = apply_config

    def on_train_start(self, trainer: Trainer, pl_module: LightningModule) -> None:
        """Reconcile local state after model and optimizer checkpoint restoration."""

        del pl_module
        if self._next_member_state is None:
            optimizer_config = self._controller.get_config()
        else:
            controller_state = self._next_member_state[CONTROLLER_STATE]
            optimizer_config = self._next_member_state[OPTIMIZER_CONFIG]
            self._controller.load_state_dict(controller_state)
            if self._controller.get_config() != dict(optimizer_config):
                raise RuntimeError("assigned controller state and optimizer configuration disagree")
        self._apply_config(trainer.optimizers, optimizer_config)


def save_local_checkpoint(
    trainer: Trainer,
    filepath: str | Path,
    *,
    weights_only: bool | None = None,
    storage_options: Any | None = None,
) -> None:
    """Save complete Lightning state from one selected process without a barrier.

    Tune invokes this only on the selected winner after the training window has
    returned. Lightning's checkpoint connector still owns serialization and the
    configured strategy still owns the write. A later DDP strategy seam must permit
    a selected nonzero rank to write.
    """

    if trainer.model is None:
        raise AttributeError("cannot save a Lightning checkpoint before fitting a model")
    checkpoint = trainer._checkpoint_connector.dump_checkpoint(weights_only)
    trainer.strategy.save_checkpoint(
        checkpoint,
        filepath,
        storage_options=storage_options,
    )
