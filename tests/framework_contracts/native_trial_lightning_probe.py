"""CPU contract probe for native trials joined by a Lightning DDP strategy.

This does not emulate Ray Tune scheduling. It isolates the framework seam that
ClanBasedTuning would rely on inside each native Tune trial:

1. independently launched trial processes join one DDP group;
2. DDP reduces their gradients without synchronizing their parameters;
3. every trial writes its own Lightning checkpoint, including nonzero ranks;
4. a target trial restarts from a source trial's checkpoint;
5. the target's mutated optimizer configuration is applied after restore; and
6. restarted trials reform the DDP group and continue diverging.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any

import torch
import torch.multiprocessing as mp
from lightning import LightningModule, Trainer
from torch import Tensor, nn
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanDDPStrategy, ClanRuntime, ClanSpec, OptimizerField


class ProbeScalarTrial(LightningModule):
    """One-parameter trial whose state is easy to audit exactly."""

    def __init__(self, initial_weight: float) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.tensor([initial_weight], dtype=torch.float32))
        self.start_state: dict[str, float | int | None] | None = None
        self.reduced_gradient: float | None = None

    def training_step(self, batch: tuple[Tensor], batch_idx: int) -> Tensor:
        del batch, batch_idx
        return self.weight.square().sum()

    def on_before_optimizer_step(self, optimizer: torch.optim.Optimizer) -> None:
        del optimizer
        if self.weight.grad is None:
            raise RuntimeError("Expected a reduced gradient before optimizer step")
        self.reduced_gradient = float(self.weight.grad.item())

    def on_train_start(self) -> None:
        optimizer = self.trainer.optimizers[0]
        optimizer_state = optimizer.state.get(self.weight, {})
        momentum = optimizer_state.get("momentum_buffer")
        self.start_state = {
            "global_step": self.trainer.global_step,
            "weight": float(self.weight.item()),
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "momentum": None if momentum is None else float(momentum.item()),
        }

    def configure_optimizers(self) -> torch.optim.Optimizer:
        # Deliberately wrong runtime LR: the strategy is authoritative for the
        # optimizer fields supplied by the trial configuration.
        return torch.optim.SGD([self.weight], lr=9.0, momentum=0.9)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _worker(
    rank: int,
    world_size: int,
    port: int,
    stage_directory: str,
    initial_weights: tuple[float, ...],
    learning_rates: tuple[float, ...],
    restore_paths: tuple[str | None, ...],
    max_steps: int,
) -> None:
    os.environ.update(
        {
            "MASTER_ADDR": "127.0.0.1",
            "MASTER_PORT": str(port),
            "WORLD_SIZE": str(world_size),
            "RANK": str(rank),
            "LOCAL_RANK": "0",
            "NODE_RANK": str(rank),
        }
    )

    trial_directory = Path(stage_directory) / f"trial-{rank}"
    trial_directory.mkdir(parents=True, exist_ok=True)

    model = ProbeScalarTrial(initial_weight=initial_weights[rank])
    clan = ClanSpec(
        population_size=world_size,
        optimizer_fields=(OptimizerField("lr", "lr"),),
        rendezvous_name="cpu-probe",
    )
    runtime = ClanRuntime(
        trial_id=f"trial-{rank}",
        actor_token=f"stage-{stage_directory}-rank-{rank}",
        session_id=0,
        global_rank=rank,
        world_size=world_size,
        master_address="127.0.0.1",
        master_port=port,
    )
    strategy = ClanDDPStrategy(
        clan,
        {"lr": learning_rates[rank]},
        runtime=runtime,
        process_group_backend="gloo",
    )
    trainer = Trainer(
        accelerator="cpu",
        devices=1,
        num_nodes=1,
        strategy=strategy,
        max_steps=max_steps,
        max_epochs=10,
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
        use_distributed_sampler=False,
        default_root_dir=trial_directory,
    )
    train_loader = DataLoader(TensorDataset(torch.zeros(1)), batch_size=1)
    trainer.fit(
        model,
        train_dataloaders=train_loader,
        ckpt_path=restore_paths[rank],
    )

    optimizer = trainer.optimizers[0]
    momentum_buffer = optimizer.state[model.weight]["momentum_buffer"]
    result = {
        "rank": rank,
        "start": model.start_state,
        "final": {
            "global_step": trainer.global_step,
            "weight": float(model.weight.item()),
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "momentum": float(momentum_buffer.item()),
            "reduced_gradient": model.reduced_gradient,
        },
    }

    checkpoint_path = trial_directory / "trial.ckpt"
    trainer.save_checkpoint(checkpoint_path)
    trainer.strategy.barrier()
    (trial_directory / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _run_stage(
    stage_directory: Path,
    *,
    initial_weights: tuple[float, float],
    learning_rates: tuple[float, float],
    restore_paths: tuple[str | None, str | None],
    max_steps: int,
) -> list[dict[str, Any]]:
    stage_directory.mkdir(parents=True, exist_ok=True)
    world_size = len(initial_weights)
    mp.spawn(
        _worker,
        args=(
            world_size,
            _free_port(),
            str(stage_directory),
            initial_weights,
            learning_rates,
            restore_paths,
            max_steps,
        ),
        nprocs=world_size,
        join=True,
    )
    return [
        json.loads((stage_directory / f"trial-{rank}" / "result.json").read_text())
        for rank in range(world_size)
    ]


def run_probe(output_directory: Path) -> dict[str, Any]:
    """Run two windows separated by an exploit-style checkpoint transition."""

    stage_one = _run_stage(
        output_directory / "window-1",
        initial_weights=(1.0, 3.0),
        learning_rates=(0.1, 0.2),
        restore_paths=(None, None),
        max_steps=1,
    )

    source_checkpoint = output_directory / "window-1" / "trial-0" / "trial.ckpt"
    target_checkpoint = output_directory / "window-1" / "trial-1" / "trial.ckpt"
    if not source_checkpoint.is_file() or not target_checkpoint.is_file():
        raise AssertionError("Every native trial, including nonzero rank, must checkpoint")

    # Simulate PBT: both source and target restart from the source checkpoint,
    # but the target receives a mutated optimizer configuration.
    stage_two = _run_stage(
        output_directory / "window-2",
        initial_weights=(-100.0, 100.0),
        learning_rates=(0.1, 0.3),
        restore_paths=(str(source_checkpoint), str(source_checkpoint)),
        max_steps=2,
    )

    report = {"window_1": stage_one, "window_2": stage_two}
    (output_directory / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    import sys

    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("native-trial-probe")
    print(json.dumps(run_probe(destination), indent=2, sort_keys=True))
