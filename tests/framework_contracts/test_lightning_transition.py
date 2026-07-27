"""Lightning 2.6 contract for winner state and member-local reconciliation."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("lightning")

import torch
from lightning import LightningModule, Trainer
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanController, ClanRound, MutationSpec
from clan_based_tuning.lightning_transition import (
    MemberStateRestore,
    apply_optimizer_config,
    save_local_checkpoint,
)
from clan_based_tuning.member_state import CONTROLLER_STATE, OPTIMIZER_CONFIG

pytestmark = pytest.mark.requires_lightning


class ScalarModel(LightningModule):
    def __init__(self, initial_weight):
        super().__init__()
        self.weight = nn.Parameter(torch.tensor([initial_weight], dtype=torch.float32))
        self.start = None

    def training_step(self, batch, batch_idx):
        del batch, batch_idx
        return self.weight.square().sum()

    def on_train_start(self):
        optimizer = self.trainer.optimizers[0]
        momentum = optimizer.state.get(self.weight, {}).get("momentum_buffer")
        self.start = {
            "global_step": self.trainer.global_step,
            "weight": float(self.weight.item()),
            "lr": optimizer.param_groups[0]["lr"],
            "momentum": None if momentum is None else float(momentum.item()),
        }

    def configure_optimizers(self):
        return torch.optim.SGD([self.weight], lr=0.1, momentum=0.9)


def _loader():
    return DataLoader(TensorDataset(torch.zeros(1)), batch_size=1)


def _trainer(tmp_path, *, max_steps, callbacks=()):
    return Trainer(
        accelerator="cpu",
        devices=1,
        max_steps=max_steps,
        max_epochs=10,
        callbacks=list(callbacks),
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
        default_root_dir=tmp_path,
    )


def _advanced_controller():
    completed = [
        ClanRound(0, 0, {"lr": 0.1}, lambda round_: None, 1.0),
        ClanRound(1, 0, {"lr": 0.2}, lambda round_: None, 0.0),
    ]
    controller = ClanController(
        member_id=1,
        population_size=2,
        initial_config={"lr": 9.0},
        mutations={
            "lr": MutationSpec(
                standard_deviation=0.0,
                geometry="linear",
                minimum=0.0,
                maximum=10.0,
            )
        },
        mode="min",
        seed=17,
        save_member_fitness=lambda round_: None,
        load_population=lambda round_index: completed,
        select_winner=lambda winner_id: None,
    )
    controller.advance()
    return controller


def _unadvanced_controller():
    return ClanController(
        member_id=1,
        population_size=2,
        initial_config={"lr": 9.0},
        mutations={
            "lr": MutationSpec(
                standard_deviation=0.0,
                geometry="linear",
                minimum=0.0,
                maximum=10.0,
            )
        },
        mode="min",
        seed=999,
        save_member_fitness=lambda round_: None,
        load_population=lambda round_index: [],
        select_winner=lambda winner_id: None,
    )


@pytest.mark.framework_contract
def test_restore_inherits_optimizer_history_then_applies_member_local_config(tmp_path):
    source_model = ScalarModel(1.0)
    source_trainer = _trainer(tmp_path / "source", max_steps=1)
    source_trainer.fit(source_model, train_dataloaders=_loader())
    source_optimizer = source_trainer.optimizers[0]
    source_weight = float(source_model.weight.item())
    source_momentum = float(source_optimizer.state[source_model.weight]["momentum_buffer"].item())
    checkpoint_path = tmp_path / "winner.ckpt"
    save_local_checkpoint(source_trainer, checkpoint_path)

    local_controller = _advanced_controller()
    local_state = {
        CONTROLLER_STATE: local_controller.state_dict(),
        OPTIMIZER_CONFIG: {"lr": 0.2},
    }
    restored_controller = _unadvanced_controller()
    restored_model = ScalarModel(-100.0)
    restore = MemberStateRestore(
        controller=restored_controller,
        next_member_state=local_state,
    )
    restored_trainer = _trainer(
        tmp_path / "target",
        max_steps=2,
        callbacks=[restore],
    )
    restored_trainer.fit(
        restored_model,
        train_dataloaders=_loader(),
        ckpt_path=checkpoint_path,
    )

    assert restored_model.start == pytest.approx(
        {
            "global_step": 1,
            "weight": source_weight,
            "lr": 0.2,
            "momentum": source_momentum,
        }
    )
    assert restored_controller.state_dict() == local_controller.state_dict()


@pytest.mark.framework_contract
def test_restore_rejects_disagreeing_controller_and_optimizer_payload():
    controller = _advanced_controller()
    restore = MemberStateRestore(
        controller=controller,
        next_member_state={
            CONTROLLER_STATE: controller.state_dict(),
            OPTIMIZER_CONFIG: {"lr": 0.3},
        },
    )

    class FakeTrainer:
        def __init__(self):
            parameter = torch.nn.Parameter(torch.ones(1))
            self.optimizers = [torch.optim.SGD([parameter], lr=0.1)]

    with pytest.raises(RuntimeError, match="disagree"):
        restore.on_train_start(FakeTrainer(), None)


@pytest.mark.framework_contract
def test_default_optimizer_applicator_rejects_unknown_field():
    optimizer = torch.optim.SGD([torch.nn.Parameter(torch.ones(1))], lr=0.1)

    with pytest.raises(KeyError, match="unknown"):
        apply_optimizer_config([optimizer], {"unknown": 1.0})


@pytest.mark.framework_contract
def test_winner_local_save_writes_a_complete_lightning_checkpoint(tmp_path):
    model = ScalarModel(1.0)
    trainer = _trainer(tmp_path / "trainer", max_steps=1)
    trainer.fit(model, train_dataloaders=_loader())
    checkpoint_path = Path(tmp_path, "local.ckpt")

    save_local_checkpoint(trainer, checkpoint_path)
    checkpoint = torch.load(checkpoint_path, weights_only=False)

    assert checkpoint["global_step"] == 1
    assert checkpoint["optimizer_states"][0]["state"]
