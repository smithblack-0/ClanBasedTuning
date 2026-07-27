"""Ray Class Trainable lifecycle for one process-local Clan member."""

from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

import ray
from lightning import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback
from ray.tune import Trainable

from clan_based_tuning.controller import ClanController
from clan_based_tuning.lightning_ddp import ClanDDPStrategy, ClanProcessGroup
from clan_based_tuning.lightning_transition import MemberStateRestore, save_local_checkpoint
from clan_based_tuning.member_state import CONTROLLER_STATE, NEXT_MEMBER_STATE
from clan_based_tuning.ray_exchange import RayControllerCallbacks
from clan_based_tuning.ray_transition import MEMBER_ID, MemberTransition

RUNTIME_EXCHANGE = "clan_runtime_exchange"
LIGHTNING_CHECKPOINT = "lightning.ckpt"

__all__ = [
    "LIGHTNING_CHECKPOINT",
    "RUNTIME_EXCHANGE",
    "ClanLightningTrainable",
    "ValidationRoundBoundary",
    "resolve_process_group",
]


class ValidationRoundBoundary(Callback):
    """Capture member-local metrics and end one Trainer window after validation."""

    def __init__(self, *, fitness_metric: str, report_metrics: Iterable[str]):
        self._fitness_metric = fitness_metric
        self._report_metrics = tuple(report_metrics)
        if fitness_metric not in self._report_metrics:
            raise ValueError("the reported metrics must include the fitness metric")
        self._result: dict[str, float] | None = None

    def on_validation_end(self, trainer: Trainer, pl_module: LightningModule) -> None:
        del pl_module
        if trainer.sanity_checking:
            return
        if self._result is not None:
            raise RuntimeError("Lightning crossed more than one Clan boundary in one step")

        self._result = {
            name: _as_float(trainer.callback_metrics[name]) for name in self._report_metrics
        }
        trainer.should_stop = True

    def result(self) -> dict[str, float]:
        if self._result is None:
            raise RuntimeError("Lightning finished without a qualifying validation boundary")
        return dict(self._result)

    @property
    def fitness(self) -> float:
        return self.result()[self._fitness_metric]


def resolve_process_group(
    *,
    exchange: Any,
    member_id: int,
    resolve=ray.get,
    host_address=ray.util.get_node_ip_address,
    reserve_port=None,
    make_token=lambda: uuid4().hex,
) -> ClanProcessGroup:
    """Join one fresh process-group window through the shared runtime actor."""

    host = host_address()
    port = (reserve_port or _find_free_port)() if member_id == 0 else None
    token = make_token()
    return resolve(
        exchange.join_process_group.remote(
            member_id=member_id,
            token=token,
            host=host,
            port=port,
        )
    )


class ClanLightningTrainable(Trainable, ABC):
    """Map one native Tune step to one qualifying Lightning validation window."""

    def setup(self, config: dict[str, Any]) -> None:
        self._member_id = config[MEMBER_ID]
        self._exchange = config[RUNTIME_EXCHANGE]
        self._next_member_state = config[NEXT_MEMBER_STATE]
        self._controller_callbacks = RayControllerCallbacks(
            exchange=self._exchange,
            member_id=self._member_id,
            resolve=self.resolve_actor_call,
        )
        self._controller = self.configure_controller(self._controller_callbacks)
        if self._controller.member_id != self._member_id:
            raise RuntimeError("configured controller and Tune member identities disagree")
        self._trainer: Trainer | None = None
        self._checkpoint_path: Path | None = None

    def step(self) -> dict[str, Any]:
        if self._next_member_state is None:
            completed_round_index = self._controller.state_dict()["round_index"]
        else:
            completed_round_index = self._next_member_state[CONTROLLER_STATE]["round_index"]
        process_group = self.join_process_group()
        restore = MemberStateRestore(
            controller=self._controller,
            next_member_state=self._next_member_state,
        )
        boundary = ValidationRoundBoundary(
            fitness_metric=self.fitness_metric(),
            report_metrics=self.report_metrics(),
        )
        strategy = ClanDDPStrategy(
            process_group,
            process_group_backend=self.process_group_backend(),
        )
        trainer = self.configure_trainer(
            strategy=strategy,
            callbacks=(restore, boundary),
        )
        if trainer.strategy is not strategy:
            raise RuntimeError("configured Trainer did not retain the supplied Clan strategy")
        if any(callback not in trainer.callbacks for callback in (restore, boundary)):
            raise RuntimeError("configured Trainer discarded a required Clan callback")

        model = self.configure_model()
        train_dataloader, val_dataloader = self.configure_dataloaders()
        trainer.fit(
            model,
            train_dataloaders=train_dataloader,
            val_dataloaders=val_dataloader,
            ckpt_path=self._checkpoint_path,
        )
        self._trainer = trainer

        metrics = boundary.result()
        self._controller.set_fitness(boundary.fitness)
        self._controller.advance()
        winner_id = self._controller_callbacks.take_selected_winner()
        transition = MemberTransition.from_controller(
            completed_round_index=completed_round_index,
            fitness=boundary.fitness,
            winner_id=winner_id,
            controller=self._controller,
        )
        return metrics | transition.as_result()

    def save_checkpoint(self, checkpoint_dir: str) -> str:
        if self._trainer is None:
            raise RuntimeError("cannot save before a Lightning window completes")
        save_local_checkpoint(
            self._trainer,
            Path(checkpoint_dir, LIGHTNING_CHECKPOINT),
        )
        return checkpoint_dir

    def load_checkpoint(self, checkpoint: str) -> None:
        checkpoint_path = Path(checkpoint, LIGHTNING_CHECKPOINT)
        if not checkpoint_path.is_file():
            raise RuntimeError("assigned Tune checkpoint has no Lightning checkpoint")
        self._checkpoint_path = checkpoint_path

    def reset_config(self, new_config: dict[str, Any]) -> bool:
        if new_config[MEMBER_ID] != self._member_id:
            raise RuntimeError("Tune cannot change a trial's Clan member identity")
        if new_config[RUNTIME_EXCHANGE] != self._exchange:
            raise RuntimeError("Tune cannot move a trial into another Clan runtime")
        self.config = new_config
        self._next_member_state = new_config[NEXT_MEMBER_STATE]
        return True

    def join_process_group(self) -> ClanProcessGroup:
        return resolve_process_group(
            exchange=self._exchange,
            member_id=self._member_id,
            resolve=self.resolve_actor_call,
        )

    @staticmethod
    def resolve_actor_call(value):
        return ray.get(value)

    @staticmethod
    def process_group_backend() -> str | None:
        return None

    @abstractmethod
    def configure_controller(
        self,
        callbacks: RayControllerCallbacks,
    ) -> ClanController:
        """Construct this trial's one persistent process-local controller."""

    @abstractmethod
    def configure_model(self) -> LightningModule:
        """Construct the model for the next Lightning window."""

    @abstractmethod
    def configure_dataloaders(self) -> tuple[Any, Any]:
        """Return the ordinary Lightning training and validation dataloaders."""

    @abstractmethod
    def configure_trainer(
        self,
        *,
        strategy: ClanDDPStrategy,
        callbacks: Sequence[Callback],
    ) -> Trainer:
        """Construct a BF16 Trainer using the supplied strategy and callbacks."""

    @abstractmethod
    def fitness_metric(self) -> str:
        """Return the member-local validation metric used for selection."""

    def report_metrics(self) -> tuple[str, ...]:
        return (self.fitness_metric(),)


def _as_float(value: Any) -> float:
    return float(value.item() if hasattr(value, "item") else value)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])
