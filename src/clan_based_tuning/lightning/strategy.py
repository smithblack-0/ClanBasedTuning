"""Lightning DDP strategy for native Ray Tune trials sharing gradients."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch
import torch.distributed as dist
from lightning import Trainer
from lightning.pytorch.strategies import DDPStrategy
from torch import nn

from clan_based_tuning.lightning.environment import _ClanRuntime
from clan_based_tuning.optimizer import OptimizerStrategy
from clan_based_tuning.spec import _ClanMetadata


class ClanDDPStrategy(DDPStrategy):
    """Apply Lightning's native DDP transform across independent Tune trials.

    The strategy owns only the boundary where ordinary Lightning assumptions do
    not fit Clan Based Training: divergence-safe DDP options, structural
    compatibility, initial population synchronization, optimizer reconciliation
    after construction and restoration, and checkpoint writes from every member.

    PyTorch ``DistributedDataParallel`` still owns gradient bucketing and
    collectives. Ray still owns trial configuration, selection, checkpoint
    cloning, transport, pause, and resume.
    """

    def __init__(
        self,
        metadata: _ClanMetadata,
        trial_config: Mapping[str, Any],
        runtime: _ClanRuntime,
        apply_optimizer_strategy: OptimizerStrategy,
        **ddp_kwargs: Any,
    ) -> None:
        if ddp_kwargs.get("init_sync") is True:
            raise ValueError("ClanDDPStrategy requires init_sync=False")
        if ddp_kwargs.get("broadcast_buffers") is True:
            raise ValueError("ClanDDPStrategy requires broadcast_buffers=False")
        ddp_kwargs["init_sync"] = False
        ddp_kwargs["broadcast_buffers"] = False

        if runtime.world_size != metadata.population_size:
            raise ValueError(
                "Resolved clan world size does not match the scheduler population size"
            )
        self._trial_config = dict(trial_config)
        self._runtime = runtime
        self._apply_optimizer_strategy = apply_optimizer_strategy
        super().__init__(**ddp_kwargs)

    @property
    def distributed_sampler_kwargs(self) -> dict[str, int]:
        """Describe the clan topology to Lightning's automatic sampler.

        Lightning's ordinary DDP strategy derives sampler topology from the
        number of processes launched by one Trainer. Clan members are instead
        independent Tune trials, so each Trainer launches one process while the
        clan runtime defines the shared world. Returning that runtime here keeps
        automatic training samplers consistent with the process group.
        """

        return {
            "num_replicas": self._runtime.world_size,
            "rank": self._runtime.global_rank,
        }

    def setup_environment(self) -> None:
        if self.num_processes != 1:
            raise RuntimeError(
                "ClanDDPStrategy requires exactly one Lightning device/process per Tune trial"
            )
        if self.num_nodes != 1:
            raise RuntimeError(
                "ClanDDPStrategy requires Trainer(num_nodes=1); the clan spans Tune trials"
            )
        super().setup_environment()

    def configure_ddp(self) -> None:
        """Verify and initialize members before Lightning applies ordinary DDP."""

        assert self.model is not None
        if any(isinstance(module, nn.SyncBatchNorm) for module in self.model.modules()):
            raise RuntimeError("SyncBatchNorm is incompatible with divergent clan members")
        self._verify_model_schema(self.model)

        fresh = self._is_fresh_trial()
        fresh_flags: list[bool | None] = [None] * self.world_size
        dist.all_gather_object(fresh_flags, fresh)
        if len(set(fresh_flags)) != 1:
            raise RuntimeError(
                "Clan members disagree on whether this window is fresh or checkpoint-restored"
            )
        if fresh:
            self._broadcast_initial_model(self.model)

        # Lightning constructs torch.nn.parallel.DistributedDataParallel here.
        # ClanBasedTuning does not implement or intercept gradient reduction.
        super().configure_ddp()
        if getattr(self.model, "broadcast_buffers", False):
            raise RuntimeError("ClanDDPStrategy failed to disable DDP buffer broadcasts")

    def setup_optimizers(self, trainer: Trainer) -> None:
        super().setup_optimizers(trainer)
        self._verify_optimizer_topology()
        # Applying on construction is idempotent when the module already built
        # its optimizer from config, and makes the default adapter fail early on
        # unsupported layouts rather than waiting for the first PBT exploit.
        self._apply_optimizer_strategy(self.optimizers, self._trial_config)

    def load_optimizer_state_dict(self, checkpoint: Mapping[str, Any]) -> None:
        super().load_optimizer_state_dict(checkpoint)
        # Lightning just restored the source member's optimizer state. Ray's
        # current target-trial config is authoritative for tuned values.
        self._apply_optimizer_strategy(self.optimizers, self._trial_config)

    def save_checkpoint(
        self,
        checkpoint: dict[str, Any],
        filepath: str | Path,
        storage_options: Any | None = None,
    ) -> None:
        # Each DDP rank is a separate Tune trial with a distinct checkpoint path.
        # Lightning's normal global-zero gate would discard all but one member.
        self.checkpoint_io.save_checkpoint(
            checkpoint,
            filepath,
            storage_options=storage_options,
        )

    def _verify_optimizer_topology(self) -> None:
        """Require checkpoint-compatible optimizer structure across members."""

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
                        "Optimizer contains a parameter outside the Lightning module"
                    ) from error
                groups.append(parameters)
            local_topology.append(
                (type(optimizer).__module__, type(optimizer).__qualname__, tuple(groups))
            )

        topologies: list[object | None] = [None] * self.world_size
        dist.all_gather_object(topologies, tuple(local_topology))
        if any(topology != tuple(local_topology) for topology in topologies):
            raise RuntimeError(
                "Clan members must have identical optimizer classes and parameter-group topology"
            )

    def _is_fresh_trial(self) -> bool:
        module = self.lightning_module
        if module is None or module.trainer is None:
            raise RuntimeError("Lightning module is not attached to a Trainer")
        checkpoint_path = module.trainer.ckpt_path
        if self._runtime.checkpoint_available and checkpoint_path is None:
            raise RuntimeError(
                "Ray supplied a trial checkpoint, but Lightning was started without "
                "ckpt_path. Materialize the Tune checkpoint and pass it to Trainer.fit()."
            )
        return checkpoint_path is None

    @staticmethod
    def _model_schema(model: nn.Module) -> tuple[tuple[Any, ...], ...]:
        modules = tuple(
            (name, type(module).__module__, type(module).__qualname__)
            for name, module in model.named_modules(remove_duplicate=False)
        )
        parameters = tuple(
            (
                name,
                tuple(parameter.shape),
                str(parameter.dtype),
                tuple(parameter.stride()),
                parameter.requires_grad,
            )
            for name, parameter in model.named_parameters(remove_duplicate=False)
        )
        buffers = tuple(
            (name, tuple(buffer.shape), str(buffer.dtype), tuple(buffer.stride()))
            for name, buffer in model.named_buffers(remove_duplicate=False)
        )
        return modules, parameters, buffers

    def _verify_model_schema(self, model: nn.Module) -> None:
        local_schema = self._model_schema(model)
        schemas: list[object | None] = [None] * self.world_size
        dist.all_gather_object(schemas, local_schema)
        if any(schema != local_schema for schema in schemas):
            raise RuntimeError(
                "Clan members must have identical module, parameter, and buffer structure"
            )

    @staticmethod
    def _broadcast_initial_model(model: nn.Module) -> None:
        with torch.no_grad():
            for parameter in model.parameters():
                dist.broadcast(parameter, src=0)
            for buffer in model.buffers():
                dist.broadcast(buffer, src=0)
