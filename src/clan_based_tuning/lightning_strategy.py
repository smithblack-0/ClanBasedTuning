"""Lightning DDP strategy for independently launched Clan Tune members.

``ClanDDPStrategy`` adapts Lightning's native DDP strategy to a world whose ranks are separate
Ray Tune trials rather than processes spawned by Lightning. Runtime discovery supplies only
the topology Lightning cannot infer. Lightning/PyTorch retain backend selection, process-group
creation, gradient reduction, barriers, and teardown; CBT additionally scopes one round
checkpoint write to the selected member and replicates Lightning-managed validation data.
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
    """Use Lightning's native DDP across independently launched Tune trials.

    Args:
        _runtime_provider: Injectable runtime discovery function used by isolated tests. Normal
            users leave this at ``join_runtime``.
        _environment_builder: Injectable topology adapter construction function. Normal users
            leave this at ``build_tune_member_environment``.
        **ddp_kwargs: Ordinary Lightning ``DDPStrategy`` keyword arguments. A custom
            ``cluster_environment`` is not allowed because CBT supplies the Tune-member
            topology. ``process_group_backend`` remains an ordinary Lightning override.

    Raises:
        TypeError: If a custom cluster environment is supplied.
        ValueError: If DDP buffer broadcasting is explicitly enabled.
        RuntimeError: During setup if Lightning resolves more than one local process/device.
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

        # DDPStrategy requires its ClusterEnvironment during construction, so runtime discovery
        # cannot be deferred to setup_environment without replacing Lightning's own lifecycle.
        runtime = _runtime_provider()
        environment = _environment_builder(runtime)
        ddp_kwargs["broadcast_buffers"] = False

        self._clan_runtime = runtime
        self._round_checkpoint_source: int | None = None
        super().__init__(cluster_environment=environment, **ddp_kwargs)

    @property
    def clan_runtime(self) -> ClanRuntime:
        """Return the stable Clan identity assigned to this Tune trial."""

        return self._clan_runtime

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
                "ClanDDPStrategy requires one Lightning process/device per Tune trial; "
                "request the trial's device through Ray and leave Trainer devices at one/auto"
            )
        super().setup_environment()

    def set_world_ranks(self) -> None:
        """Keep the externally assigned cross-trial rank and world size unchanged."""

        rank_zero_only.rank = utilities_rank_zero_only.rank = self.global_rank

    def begin_round_checkpoint(self, source_rank: int) -> None:
        """Scope the next Lightning checkpoint persistence to the selected Clan member."""

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
