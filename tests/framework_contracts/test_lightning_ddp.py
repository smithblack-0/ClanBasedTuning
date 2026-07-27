"""CPU process contract for cross-trial Lightning DDP behavior."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest

pytest.importorskip("lightning")

import torch
import torch.multiprocessing as mp
from lightning import LightningModule, Trainer
from torch import nn
from torch.multiprocessing.spawn import ProcessRaisedException
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanController, MutationSpec
from clan_based_tuning.lightning_ddp import ClanDDPStrategy, ClanProcessGroup
from clan_based_tuning.lightning_transition import (
    MemberStateRestore,
    save_local_checkpoint,
)

pytestmark = pytest.mark.requires_lightning


class ScalarMember(LightningModule):
    def __init__(self, initial_weight):
        super().__init__()
        self.weight = nn.Parameter(torch.tensor([initial_weight], dtype=torch.float32))
        self.reduced_gradient = None

    def training_step(self, batch, batch_idx):
        del batch, batch_idx
        return self.weight.square().sum()

    def on_before_optimizer_step(self, optimizer):
        del optimizer
        self.reduced_gradient = float(self.weight.grad.item())

    def configure_optimizers(self):
        return torch.optim.SGD([self.weight], lr=9.0)


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _controller(rank):
    return ClanController(
        member_id=rank,
        population_size=2,
        initial_config={"lr": [0.1, 0.2][rank]},
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
        load_population=lambda round_index: [],
        select_winner=lambda winner_id: None,
    )


def _worker(rank, port, output_directory):
    os.environ["GLOO_SOCKET_IFNAME"] = "lo"
    process_group = ClanProcessGroup(
        global_rank=rank,
        world_size=2,
        master_address="127.0.0.1",
        master_port=port,
    )
    model = ScalarMember(initial_weight=[1.0, 3.0][rank])
    trainer = Trainer(
        accelerator="cpu",
        devices=1,
        num_nodes=1,
        strategy=ClanDDPStrategy(process_group, process_group_backend="gloo"),
        precision="bf16-mixed",
        callbacks=[
            MemberStateRestore(
                controller=_controller(rank),
                next_member_state=None,
            )
        ],
        max_steps=1,
        max_epochs=10,
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
        use_distributed_sampler=False,
        default_root_dir=Path(output_directory, f"member-{rank}"),
    )
    trainer.fit(
        model,
        train_dataloaders=DataLoader(TensorDataset(torch.zeros(1)), batch_size=1),
    )
    if rank == 1:
        save_local_checkpoint(trainer, Path(output_directory, "member-1.ckpt"))
    Path(output_directory, f"member-{rank}.json").write_text(
        json.dumps(
            {
                "gradient": model.reduced_gradient,
                "weight": float(model.weight.item()),
                "lr": trainer.optimizers[0].param_groups[0]["lr"],
            }
        )
    )


@pytest.mark.framework_contract
def test_native_ddp_shares_gradient_then_local_optimizers_diverge(tmp_path):
    try:
        mp.spawn(
            _worker,
            args=(_free_port(), str(tmp_path)),
            nprocs=2,
            join=True,
        )
    except ProcessRaisedException as error:
        if "ProcessGroupGloo" in str(error) and "Operation not permitted" in str(error):
            pytest.skip("sandbox denied the socket operation required by ProcessGroupGloo")
        raise
    members = [json.loads(Path(tmp_path, f"member-{rank}.json").read_text()) for rank in range(2)]

    assert members[0]["gradient"] == pytest.approx(2.0)
    assert members[1]["gradient"] == pytest.approx(2.0)
    assert members[0]["lr"] == pytest.approx(0.1)
    assert members[1]["lr"] == pytest.approx(0.2)
    assert members[0]["weight"] == pytest.approx(0.8)
    assert members[1]["weight"] == pytest.approx(0.6)

    winner_checkpoint = Path(tmp_path, "member-1.ckpt")
    assert winner_checkpoint.is_file()
    checkpoint = torch.load(winner_checkpoint, weights_only=False)
    assert checkpoint["state_dict"]["weight"].item() == pytest.approx(0.6)


@pytest.mark.framework_contract
def test_strategy_requires_native_init_sync_and_disables_buffer_broadcast():
    process_group = ClanProcessGroup(
        global_rank=0,
        world_size=2,
        master_address="127.0.0.1",
        master_port=12345,
    )

    with pytest.raises(ValueError, match="initial state synchronization"):
        ClanDDPStrategy(process_group, init_sync=False)
    with pytest.raises(ValueError, match="broadcast_buffers"):
        ClanDDPStrategy(process_group, broadcast_buffers=True)


@pytest.mark.framework_contract
def test_strategy_rejects_non_bf16_and_ordinary_checkpoint_callbacks():
    process_group = ClanProcessGroup(
        global_rank=0,
        world_size=2,
        master_address="127.0.0.1",
        master_port=12345,
    )

    class FakeTrainer:
        def __init__(self):
            self.precision = "32-true"
            self.checkpoint_callbacks = []

    strategy = ClanDDPStrategy(process_group)
    trainer = FakeTrainer()
    with pytest.raises(RuntimeError, match="BF16"):
        strategy.setup(trainer)

    trainer.precision = "bf16-mixed"
    trainer.checkpoint_callbacks = [object()]
    with pytest.raises(RuntimeError, match="disable ordinary"):
        strategy.setup(trainer)
