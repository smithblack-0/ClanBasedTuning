"""One realistic-but-small workload shared across environment qualification.

CPU, CUDA/NCCL, multi-node, destructive-failure, and benchmark paths should differ in the
thing they are qualifying—not in model/training semantics. This module therefore centralizes a
two-layer regression model, AdamW, fixed synthetic data, two training batches per invocation,
and the same Clan scheduler/search space. Changes here intentionally affect every realistic
qualification path and should be reviewed as changes to the common test workload.

The workload is large enough to exercise real forward/backward, optimizer-state restoration,
userspace genome application, DDP topology/backend selection, and Tune checkpoint
continuation, but small enough to run without a model/dataset download.
"""

import os
import tempfile
import zlib
from datetime import timedelta
from pathlib import Path
from typing import Any

import lightning.pytorch as lightning
import ray
import torch
import torch.distributed as torch_distributed
from ray import tune
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback

_EXTRA_METRICS = [
    "lr_seen",
    "weight_decay_seen",
    "restored_global_step",
    "device_is_cuda",
    "backend_is_nccl",
    "node_fingerprint",
    "world_size_seen",
]


class TinyRegressionModel(lightning.LightningModule):
    """Make inherited optimizer state and runtime topology observable in a real training loop.

    The model owns its optimizer exactly as user code does in the public API. Runtime facts are
    sampled after Lightning starts training and surfaced as validation metrics so framework
    contracts can verify restore order, userspace genome application, backend/device choice,
    and physical-node placement without reaching into CBT internals.
    """

    def __init__(self, genome: dict[str, Any]) -> None:
        super().__init__()
        self.genome = genome
        self.network = torch.nn.Sequential(
            torch.nn.Linear(4, 8),
            torch.nn.Tanh(),
            torch.nn.Linear(8, 1),
        )
        self.optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=float(genome["lr"]),
            weight_decay=float(genome["weight_decay"]),
        )
        self.restored_global_step = 0.0
        self.device_is_cuda = 0.0
        self.backend_is_nccl = 0.0
        self.node_fingerprint = 0.0
        self.world_size_seen = 0.0

    def on_train_start(self) -> None:
        """Exercise the documented userspace seam after Lightning has restored optimizer state.

        Applying the child genome here is the behavior the package promises users: CBT provides
        config values but never edits the optimizer. Capturing ``global_step`` at the same hook
        proves resumed invocations reached this code after Lightning restoration.
        """

        for param_group in self.optimizer.param_groups:
            param_group["lr"] = float(self.genome["lr"])
            param_group["weight_decay"] = float(self.genome["weight_decay"])

        self.restored_global_step = float(self.trainer.global_step)
        self.device_is_cuda = float(self.device.type == "cuda")
        self.backend_is_nccl = float(
            torch_distributed.is_initialized()
            and str(torch_distributed.get_backend()).lower() == "nccl"
        )
        self.node_fingerprint = float(zlib.crc32(ray.util.get_node_ip_address().encode("utf-8")))
        self.world_size_seen = float(self.trainer.strategy.world_size)

    def training_step(self, batch: list[torch.Tensor], batch_index: int) -> torch.Tensor:
        """Run ordinary regression, with one opt-in hard-exit path for failure qualification.

        The crash keys are absent from normal qualification configs. When explicitly supplied,
        ``os._exit`` kills the process without Lightning cleanup so the destructive contract
        exercises real active-collective peer loss rather than a graceful exception path.
        """

        del batch_index
        if "crash_member_id" in self.genome:
            member_id = self.trainer.strategy.clan_runtime.member_id
            crash_member_id = int(self.genome["crash_member_id"])
            crash_after_global_step = int(self.genome["crash_after_global_step"])
            if member_id == crash_member_id and self.trainer.global_step >= crash_after_global_step:
                os._exit(17)

        features, target = batch
        prediction = self.network(features)
        return torch.nn.functional.mse_loss(prediction, target)

    def validation_step(self, batch: list[torch.Tensor], batch_index: int) -> None:
        """Produce member-local fitness on the validation workload CBT must replicate exactly."""

        del batch_index
        features, target = batch
        prediction = self.network(features)
        loss = torch.nn.functional.mse_loss(prediction, target)
        self.log("val_loss", loss, on_step=False, on_epoch=True)

    def on_validation_epoch_end(self) -> None:
        """Publish observability facts only at real, reportable validation boundaries."""

        if self.trainer.sanity_checking:
            return
        self.log("lr_seen", float(self.optimizer.param_groups[0]["lr"]))
        self.log("weight_decay_seen", float(self.optimizer.param_groups[0]["weight_decay"]))
        self.log("restored_global_step", self.restored_global_step)
        self.log("device_is_cuda", self.device_is_cuda)
        self.log("backend_is_nccl", self.backend_is_nccl)
        self.log("node_fingerprint", self.node_fingerprint)
        self.log("world_size_seen", self.world_size_seen)

    def configure_optimizers(self) -> torch.optim.Optimizer:
        """Give Lightning the same user-owned optimizer whose history crosses generations."""

        return self.optimizer


def train_tiny_mlp_member(genome: dict[str, Any]) -> None:
    """Run the shared workload through the same ordinary Tune-function API a user would write.

    Checkpoint handling intentionally uses only ``tune.get_checkpoint`` plus Lightning's normal
    ``ckpt_path`` restore. Keeping this helper realistic prevents hardware tests from quietly
    qualifying a special CBT-only execution path that examples/users do not exercise.
    """

    torch.manual_seed(17)
    if str(genome["accelerator"]) == "cpu":
        torch.set_num_threads(1)

    model = TinyRegressionModel(genome)
    checkpoint = tune.get_checkpoint()

    with tempfile.TemporaryDirectory() as local_checkpoint_dir:
        checkpoint_path = None
        if checkpoint is not None:
            checkpoint_dir = checkpoint.to_directory(local_checkpoint_dir)
            checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")

        features = torch.arange(32, dtype=torch.float32).reshape(8, 4) / 32.0
        targets = 0.5 * features.sum(dim=1, keepdim=True)
        train_data = DataLoader(
            TensorDataset(features, targets),
            batch_size=2,
            shuffle=False,
        )
        validation_data = DataLoader(
            TensorDataset(features, targets),
            batch_size=4,
            shuffle=False,
        )
        trainer = lightning.Trainer(
            accelerator=str(genome["accelerator"]),
            devices=1,
            strategy=ClanDDPStrategy(timeout=timedelta(seconds=float(genome["ddp_timeout_s"]))),
            callbacks=[ClanTuneReportCallback(extra_metrics=_EXTRA_METRICS)],
            max_epochs=100,
            logger=False,
            enable_checkpointing=False,
            enable_model_summary=False,
            enable_progress_bar=False,
            num_sanity_val_steps=0,
            limit_train_batches=2,
        )
        trainer.fit(
            model,
            train_dataloaders=train_data,
            val_dataloaders=validation_data,
            ckpt_path=str(checkpoint_path) if checkpoint_path is not None else None,
        )


def build_tiny_scheduler(*, join_timeout_s: float = 60.0) -> ClanScheduler:
    """Keep scheduler/mutation semantics identical across all realistic qualification paths.

    Tests may vary the rendezvous timeout when failure behavior is the dimension under test;
    population shape, mutation geometry, seed, and bounds stay fixed so GPU/multi-node results
    remain comparable to the CPU baseline.
    """

    return ClanScheduler(
        population_size=2,
        mutations={
            "lr": {
                "standard_deviation": 0.15,
                "geometry": "log",
                "minimum": 1e-4,
                "maximum": 0.1,
            },
            "weight_decay": {
                "standard_deviation": 0.10,
                "geometry": "log",
                "minimum": 1e-5,
                "maximum": 0.1,
            },
        },
        seed=7,
        join_timeout_s=join_timeout_s,
    )


def tiny_param_space(*, accelerator: str, ddp_timeout_s: float = 30.0) -> dict[str, Any]:
    """Vary only execution environment while preserving the two initial candidate genomes.

    Centralizing the Tune config prevents CUDA/multi-node/failure tests from accidentally
    changing optimizer starting points while claiming to qualify only an environment change.
    """

    return {
        "lr": tune.grid_search([0.01, 0.02]),
        "weight_decay": 0.01,
        "accelerator": accelerator,
        "ddp_timeout_s": ddp_timeout_s,
    }


def tiny_tune_config(scheduler: ClanScheduler) -> tune.TuneConfig:
    """Bind every realistic contract to the same fitness name and minimization direction.

    This helper is intentionally shared because worker and driver selection must agree on these
    values; copying them into each hardware test would create needless drift risk.
    """

    return tune.TuneConfig(
        scheduler=scheduler,
        metric="val_loss",
        mode="min",
    )
