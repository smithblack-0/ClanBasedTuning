"""Lightning DDP strategy for independently launched Clan Tune members.

``ClanDDPStrategy`` keeps Lightning/PyTorch in charge of DDP while adapting two assumptions
that do not hold for CBT: ranks are separate Tune trials rather than Lightning-spawned local
processes, and the checkpoint writer changes each generation with the selected winner.
Runtime discovery supplies the external topology; Lightning still owns backend selection,
process-group creation, gradient reduction, barriers, optimizer restore, and teardown.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from lightning.pytorch.strategies import DDPStrategy
from lightning.pytorch.utilities.rank_zero import rank_zero_only
from lightning_utilities.core.rank_zero import rank_zero_only as utilities_rank_zero_only

from clan_based_tuning.cohort import ClanRuntime
from clan_based_tuning.lightning_environment import (
    TuneMemberEnvironment,
    build_tune_member_environment,
)
from clan_based_tuning.runtime import join_runtime

# Main


class ClanDDPStrategy(DDPStrategy):
    """Run native Lightning DDP across one independently launched Tune process per member.

    Construction resolves Clan runtime before ``DDPStrategy`` is initialized because
    Lightning requires a ``ClusterEnvironment`` during base-strategy construction. This is an
    intentional framework-lifecycle constraint, not hidden CBT process creation: runtime
    discovery joins already-launched Tune workers and returns topology facts only.

    ``broadcast_buffers`` is forced off because buffers belong to each candidate's diverged
    model state after the shared-gradient point. Broadcasting them from one rank would silently
    couple candidates outside the intended DDP gradient synchronization.

    Args:
        _runtime_provider: Runtime discovery seam. Replacements must return the stable identity
            and rendezvous assigned to the current Tune trial without creating a second process.
        _environment_builder: Translation seam from Clan runtime to Lightning's fixed external
            topology contract.
        **ddp_kwargs: Ordinary Lightning ``DDPStrategy`` options. Backend and timeout remain
            Lightning-owned; a custom ``cluster_environment`` is rejected because it would
            conflict with the scheduler-assigned world.
    """

    def __init__(
        self,
        *,
        _runtime_provider: Callable[[], ClanRuntime] = join_runtime,
        _environment_builder: Callable[[ClanRuntime], TuneMemberEnvironment] = (
            build_tune_member_environment
        ),
        **ddp_kwargs: Any,
    ) -> None:
        if "cluster_environment" in ddp_kwargs:
            raise TypeError("ClanDDPStrategy supplies its Tune-member cluster environment")
        if "broadcast_buffers" in ddp_kwargs and ddp_kwargs["broadcast_buffers"] is True:
            raise ValueError("Clan members require broadcast_buffers=False after DDP setup")

        # DDPStrategy consumes ClusterEnvironment during __init__. Deferring discovery to
        # setup_environment would require replacing Lightning's construction lifecycle rather
        # than adapting it, so resolve only the already-existing external runtime here.
        runtime = _runtime_provider()
        environment = _environment_builder(runtime)
        ddp_kwargs["broadcast_buffers"] = False

        self._clan_runtime = runtime
        self._round_checkpoint_source: int | None = None
        super().__init__(cluster_environment=environment, **ddp_kwargs)

    @property
    def clan_runtime(self) -> ClanRuntime:
        """Expose the already-resolved member identity to the reporting callback.

        The callback must use the same runtime that created this DDP strategy; rediscovering it
        independently could observe a different invocation during retry/restore.
        """

        return self._clan_runtime

    @property
    def distributed_sampler_kwargs(self) -> dict[str, int]:
        """Partition training but replicate Lightning-managed validation across candidates.

        Training must retain ordinary DDP partitioning so all ranks contribute to one shared
        gradient stream. Candidate fitness, however, is comparable only when every member sees
        the same full validation workload, so Lightning's automatic validation sampler is
        presented as a one-replica rank-zero sampler on every process. Explicit user-provided
        distributed samplers remain user-owned.
        """

        trainer = self.lightning_module.trainer if self.lightning_module is not None else None
        if trainer is not None and (trainer.validating or trainer.sanity_checking):
            return {"num_replicas": 1, "rank": 0}
        return {"num_replicas": self.world_size, "rank": self.global_rank}

    def setup_environment(self) -> None:
        """Reject nested local spawning, then let Lightning perform normal DDP setup.

        One Tune trial must correspond to exactly one Lightning process/device. If Lightning
        resolves more than one local process, proceeding would create ranks that the scheduler
        never registered and break stable member identity.
        """

        if self.num_processes != 1:
            raise RuntimeError(
                "ClanDDPStrategy requires one Lightning process/device per Tune trial; "
                "request the trial's device through Ray and leave Trainer devices at one/auto"
            )
        super().setup_environment()

    def set_world_ranks(self) -> None:
        """Preserve ranks assigned across Tune trials instead of letting Lightning recompute them.

        Normal ``DDPStrategy`` derives global rank from Lightning's own node/local launch
        topology. CBT's processes were launched independently by Tune and already have stable
        global ranks from ``TuneMemberEnvironment``. Updating only Lightning's rank-zero helper
        state keeps decorators/logging aligned without replacing the external assignment.
        """

        rank_zero_only.rank = utilities_rank_zero_only.rank = self.global_rank

    def begin_round_checkpoint(self, source_rank: int) -> None:
        """Temporarily select which Clan member may persist the round continuation.

        Every rank still enters ``Trainer.save_checkpoint`` so Lightning's checkpoint hooks and
        post-save barrier remain symmetric. This flag changes only the physical writer; it does
        not bypass checkpoint construction on losing members.
        """

        if self._round_checkpoint_source is not None:
            raise RuntimeError("a Clan round checkpoint is already active")
        if not 0 <= source_rank < self.world_size:
            raise ValueError("checkpoint source rank must identify one Clan member")
        self._round_checkpoint_source = source_rank

    def end_round_checkpoint(self) -> None:
        """End the temporary winner-only write scope before user checkpointing can continue.

        Failing to clear this state would make later ordinary Lightning checkpoints silently
        winner-gated, so an unmatched begin/end pair is treated as lifecycle corruption.
        """

        if self._round_checkpoint_source is None:
            raise RuntimeError("no Clan round checkpoint is active")
        self._round_checkpoint_source = None

    def save_checkpoint(
        self,
        checkpoint: dict[str, Any],
        filepath: str | Path,
        storage_options: Any | None = None,
    ) -> None:
        """Change only the round's physical writer while preserving Lightning checkpoint flow.

        Outside a Clan round, delegate unchanged to Lightning. During a round, the selected
        member writes through the configured ``CheckpointIO`` while losing ranks return from
        this strategy hook; ``Trainer.save_checkpoint`` still executes its normal barrier after
        the hook on every rank. This is necessary because CBT's winner is dynamic and need not
        be global rank zero.
        """

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
