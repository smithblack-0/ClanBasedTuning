"""Lightning DDP strategy for one Tune function trial per Clan member."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lightning.pytorch.strategies import DDPStrategy
from lightning.pytorch.utilities.rank_zero import rank_zero_only
from lightning_utilities.core.rank_zero import rank_zero_only as utilities_rank_zero_only

from clan_based_tuning.lightning_environment import TuneMemberEnvironment
from clan_based_tuning.runtime import current_runtime


class ClanDDPStrategy(DDPStrategy):
    """Use Lightning's native DDP across independently launched Tune trials.

    The strategy supplies only topology facts that Lightning cannot infer across separate
    Tune trials. Backend selection, process-group initialization, collectives, gradient
    reduction, and teardown remain Lightning/PyTorch responsibilities.

    Training uses ordinary DDP data partitioning. When Lightning auto-injects a sampler
    for validation (including sanity validation), every Clan member instead receives the
    full validation dataset so candidate fitness is evaluated on the same held-out data.
    Explicit user-supplied distributed samplers remain user-owned and are not replaced.

    Per-forward buffer broadcast is disabled so one member's post-update buffers cannot
    overwrite another member's local state. CBT round checkpointing temporarily selects
    one rank as the writer; every rank still participates in Lightning checkpoint
    construction and the Trainer's post-save barrier.
    """

    def __init__(self, **ddp_kwargs: Any) -> None:
        if "cluster_environment" in ddp_kwargs:
            raise TypeError("ClanDDPStrategy supplies its Tune-member cluster environment")
        if ddp_kwargs.get("broadcast_buffers") is True:
            raise ValueError("Clan members require broadcast_buffers=False after DDP setup")

        runtime = current_runtime()
        environment = TuneMemberEnvironment(
            global_rank=runtime.member_id,
            world_size=runtime.world_size,
            local_rank=0,
            node_rank=runtime.member_id,
            main_address=runtime.main_address,
            main_port=runtime.main_port,
        )
        ddp_kwargs["broadcast_buffers"] = False

        self._round_checkpoint_source: int | None = None
        super().__init__(cluster_environment=environment, **ddp_kwargs)

    @property
    def distributed_sampler_kwargs(self) -> dict[str, int]:
        """Partition training while replicating Lightning-managed validation data."""

        trainer = self.lightning_module.trainer if self.lightning_module is not None else None
        if trainer is not None and (trainer.validating or trainer.sanity_checking):
            return {"num_replicas": 1, "rank": 0}
        return {"num_replicas": self.world_size, "rank": self.global_rank}

    def setup_environment(self) -> None:
        """Enter ordinary DDP setup without asking Lightning to spawn another process."""

        if self.num_processes != 1:
            raise RuntimeError(
                "the initial Clan DDP path requires exactly one Lightning device/process "
                "per Tune trial"
            )
        super().setup_environment()

    def set_world_ranks(self) -> None:
        """Keep the externally assigned cross-trial rank and world size unchanged."""

        rank_zero_only.rank = utilities_rank_zero_only.rank = self.global_rank

    def begin_round_checkpoint(self, source_rank: int) -> None:
        """Scope the next Lightning checkpoint write to the selected Clan member."""

        if self._round_checkpoint_source is not None:
            raise RuntimeError("a Clan round checkpoint is already active")
        if not 0 <= source_rank < self.world_size:
            raise ValueError("checkpoint source rank must identify one Clan member")
        self._round_checkpoint_source = source_rank

    def end_round_checkpoint(self) -> None:
        """Return later user-requested checkpoints to ordinary Lightning semantics."""

        if self._round_checkpoint_source is None:
            raise RuntimeError("no Clan round checkpoint is active")
        self._round_checkpoint_source = None

    def save_checkpoint(
        self,
        checkpoint: dict[str, Any],
        filepath: str | Path,
        storage_options: Any | None = None,
    ) -> None:
        """Persist only the selected round source while Trainer retains its barrier."""

        source_rank = self._round_checkpoint_source
        if source_rank is None:
            super().save_checkpoint(checkpoint, filepath, storage_options=storage_options)
            return
        if self.global_rank == source_rank:
            self.checkpoint_io.save_checkpoint(
                checkpoint,
                filepath,
                storage_options=storage_options,
            )
