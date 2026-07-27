"""Lightning-native DDP configuration for a Clan spanning Tune trials."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch.distributed as dist
from lightning import Trainer
from lightning.pytorch.plugins.environments import ClusterEnvironment
from lightning.pytorch.strategies import DDPStrategy
from torch import nn

__all__ = [
    "ClanDDPStrategy",
    "ClanLightningEnvironment",
    "ClanProcessGroup",
]


@dataclass(frozen=True, slots=True)
class ClanProcessGroup:
    """Externally resolved identity for one member in a Clan process group."""

    global_rank: int
    world_size: int
    master_address: str
    master_port: int

    def __post_init__(self) -> None:
        if self.world_size < 2:
            raise ValueError("Clan DDP requires at least two members")
        if not 0 <= self.global_rank < self.world_size:
            raise ValueError("global rank must identify one Clan member")
        if not self.master_address:
            raise ValueError("master address must be non-empty")
        if not 0 < self.master_port < 65536:
            raise ValueError("master port must be valid")


class ClanLightningEnvironment(ClusterEnvironment):
    """Present externally launched Tune trial processes to Lightning."""

    def __init__(self, process_group: ClanProcessGroup):
        super().__init__()
        self._process_group = process_group

    @property
    def creates_processes_externally(self) -> bool:
        return True

    @property
    def main_address(self) -> str:
        return self._process_group.master_address

    @property
    def main_port(self) -> int:
        return self._process_group.master_port

    @staticmethod
    def detect() -> bool:
        return False

    def world_size(self) -> int:
        return self._process_group.world_size

    def set_world_size(self, size: int) -> None:
        del size

    def global_rank(self) -> int:
        return self._process_group.global_rank

    def set_global_rank(self, rank: int) -> None:
        del rank

    def local_rank(self) -> int:
        return 0

    def node_rank(self) -> int:
        return 0

    def teardown(self) -> None:
        return None


class ClanDDPStrategy(DDPStrategy):
    """Keep native DDP mechanics while preserving divergent Clan members."""

    def __init__(self, process_group: ClanProcessGroup, **ddp_kwargs: Any):
        if ddp_kwargs.get("init_sync", True) is not True:
            raise ValueError("Clan DDP requires native initial state synchronization")
        if ddp_kwargs.get("broadcast_buffers", False) is not False:
            raise ValueError("Clan DDP requires broadcast_buffers=False")
        ddp_kwargs["init_sync"] = True
        ddp_kwargs["broadcast_buffers"] = False
        self._clan_process_group = process_group
        ddp_kwargs["cluster_environment"] = ClanLightningEnvironment(process_group)
        super().__init__(**ddp_kwargs)

    @property
    def distributed_sampler_kwargs(self) -> dict[str, int]:
        """Expose the cross-trial world instead of the one-device local Trainer."""

        return {
            "num_replicas": self._clan_process_group.world_size,
            "rank": self._clan_process_group.global_rank,
        }

    def setup(self, trainer: Trainer) -> None:
        if trainer.precision not in {"bf16-mixed", "bf16-true"}:
            raise RuntimeError("the supported Clan DDP path requires BF16 precision")
        if trainer.checkpoint_callbacks:
            raise RuntimeError(
                "disable ordinary Lightning checkpoint callbacks; Tune saves only the winner"
            )
        super().setup(trainer)

    def setup_environment(self) -> None:
        if self.num_processes != 1 or self.num_nodes != 1:
            raise RuntimeError(
                "ClanDDPStrategy requires one Lightning device and one node per Tune trial"
            )
        super().setup_environment()

    def configure_ddp(self) -> None:
        assert self.model is not None
        if any(isinstance(module, nn.SyncBatchNorm) for module in self.model.modules()):
            raise RuntimeError("SyncBatchNorm would combine divergent member buffers")
        super().configure_ddp()
        if getattr(self.model, "broadcast_buffers", False):
            raise RuntimeError("Lightning did not preserve broadcast_buffers=False")

    def setup_optimizers(self, trainer: Trainer) -> None:
        super().setup_optimizers(trainer)
        self._verify_optimizer_topology()

    def save_checkpoint(
        self,
        checkpoint: dict[str, Any],
        filepath: str | Path,
        storage_options: Any | None = None,
    ) -> None:
        """Permit the externally selected member to write, regardless of DDP rank."""

        self.checkpoint_io.save_checkpoint(
            checkpoint,
            filepath,
            storage_options=storage_options,
        )

    def _verify_optimizer_topology(self) -> None:
        module = self.lightning_module
        if module is None:
            raise RuntimeError("Lightning module is unavailable during optimizer setup")
        parameter_indices = {
            id(parameter): index for index, parameter in enumerate(module.parameters())
        }
        local_topology = []
        for optimizer in self.optimizers:
            groups = []
            for group in optimizer.param_groups:
                try:
                    parameters = tuple(
                        parameter_indices[id(parameter)] for parameter in group["params"]
                    )
                except KeyError as error:
                    raise RuntimeError(
                        "optimizer contains a parameter outside the Lightning module"
                    ) from error
                groups.append(parameters)
            local_topology.append(
                (type(optimizer).__module__, type(optimizer).__qualname__, tuple(groups))
            )

        gathered: list[object | None] = [None] * self.world_size
        dist.all_gather_object(gathered, tuple(local_topology))
        if any(topology != tuple(local_topology) for topology in gathered):
            raise RuntimeError(
                "Clan members require identical optimizer classes and parameter groups"
            )
