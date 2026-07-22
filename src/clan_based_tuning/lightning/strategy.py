"""Lightning DDP strategy for native Ray Tune trials sharing gradients."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch
import torch.distributed as dist
from lightning import Trainer
from lightning.pytorch.callbacks import EarlyStopping
from lightning.pytorch.strategies import DDPStrategy
from torch import nn

from clan_based_tuning.lightning.environment import ClanClusterEnvironment, ClanRuntime
from clan_based_tuning.optimizer import apply_optimizer_config
from clan_based_tuning.spec import ClanSpec

_TUNED_VALUE = "<clan-tuned>"


class ClanDDPStrategy(DDPStrategy):
    """Make one native Tune trial a rank in a shared-gradient clan.

    Ray remains authoritative for trial identity, configuration, checkpoint
    cloning, pause, and resume. This strategy owns only the Lightning/DDP seam:
    external rank setup, divergence-preserving DDP options, one-time structural
    verification, fresh-population initialization, optimizer gene application,
    and trial-local checkpoint writes.
    """

    def __init__(
        self,
        clan: ClanSpec,
        trial_config: Mapping[str, Any],
        *,
        runtime: ClanRuntime | None = None,
        cluster_environment: Any | None = None,
        **ddp_kwargs: Any,
    ) -> None:
        for unsupported_key in (
            "ddp_comm_state",
            "ddp_comm_hook",
            "ddp_comm_wrapper",
            "model_averaging_period",
        ):
            if ddp_kwargs.get(unsupported_key) is not None:
                raise ValueError(f"ClanDDPStrategy does not support {unsupported_key}")
        if cluster_environment is not None:
            raise ValueError(
                "ClanDDPStrategy owns the cluster environment; do not supply one"
            )
        if ddp_kwargs.get("init_sync") is True:
            raise ValueError("ClanDDPStrategy requires init_sync=False")
        if ddp_kwargs.get("broadcast_buffers") is True:
            raise ValueError("ClanDDPStrategy requires broadcast_buffers=False")

        ddp_kwargs["init_sync"] = False
        ddp_kwargs["broadcast_buffers"] = False

        self._trial_config = dict(trial_config)
        self.clan = clan.resolve_trial_config(self._trial_config)
        self.runtime = runtime or self._resolve_tune_runtime()
        if self.runtime.world_size != self.clan.population_size:
            raise ValueError(
                "Resolved clan world size does not match ClanSpec.population_size"
            )

        super().__init__(
            cluster_environment=ClanClusterEnvironment(self.runtime),
            **ddp_kwargs,
        )

    def setup(self, trainer: Trainer) -> None:
        if trainer.checkpoint_callbacks:
            raise RuntimeError(
                "Lightning checkpoint callbacks are unsupported. Use "
                "ClanBase.tune_report_callback(), which reports each native trial's "
                "checkpoint to Ray PBT."
            )
        if any(isinstance(callback, EarlyStopping) for callback in trainer.callbacks):
            raise RuntimeError(
                "Lightning EarlyStopping is incompatible with a coupled clan. "
                "Use a Ray Tune stopping condition that stops the complete population."
            )
        super().setup(trainer)

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
        super().configure_ddp()
        self._verify_runtime_ddp_invariants()

    def setup_optimizers(self, trainer: Trainer) -> None:
        super().setup_optimizers(trainer)
        if self.lightning_module is None or not self.lightning_module.automatic_optimization:
            raise RuntimeError("ClanBasedTraining requires Lightning automatic optimization")
        if len(self.optimizers) != 1:
            raise RuntimeError("ClanBasedTraining currently supports exactly one optimizer")
        self._verify_optimizer_schema(self.optimizers[0])
        if self.lr_scheduler_configs:
            raise RuntimeError(
                "Lightning learning-rate schedulers are unsupported because the clan "
                "scheduler owns optimizer hyperparameter evolution"
            )
        self._apply_trial_optimizer_config()

    def load_optimizer_state_dict(self, checkpoint: Mapping[str, Any]) -> None:
        super().load_optimizer_state_dict(checkpoint)
        # Ray PBT restores the source trial's optimizer state. The target trial's
        # mutated config is authoritative for the fields declared by ClanSpec.
        self._apply_trial_optimizer_config()

    def save_checkpoint(
        self,
        checkpoint: dict[str, Any],
        filepath: str | Path,
        storage_options: Any | None = None,
    ) -> None:
        # Every DDP rank is a separate native Tune trial with a distinct path.
        # Lightning's ordinary global-zero gate would discard all but one trial.
        self.checkpoint_io.save_checkpoint(
            checkpoint,
            filepath,
            storage_options=storage_options,
        )

    def _verify_optimizer_schema(self, optimizer: torch.optim.Optimizer) -> None:
        module = self.lightning_module
        if module is None:
            raise RuntimeError("Lightning module is unavailable during optimizer setup")
        parameter_indices = {
            id(parameter): index for index, parameter in enumerate(module.parameters())
        }
        groups = []
        for group_index, group in enumerate(optimizer.param_groups):
            try:
                parameters = tuple(
                    parameter_indices[id(parameter)] for parameter in group["params"]
                )
            except KeyError as error:
                raise RuntimeError(
                    "Optimizer contains a parameter outside the Lightning module"
                ) from error
            static_values = tuple(
                sorted(
                    (
                        key,
                        self._optimizer_static_value(group_index, key, value),
                    )
                    for key, value in group.items()
                    if key != "params"
                )
            )
            groups.append((parameters, static_values))
        local_schema = (
            type(optimizer).__module__,
            type(optimizer).__qualname__,
            tuple(groups),
        )
        schemas: list[object | None] = [None] * self.world_size
        dist.all_gather_object(schemas, local_schema)
        if any(schema != local_schema for schema in schemas):
            raise RuntimeError(
                "Clan members must have identical optimizer classes, parameter-group "
                "structure, and untuned optimizer settings"
            )

    def _optimizer_static_value(self, group_index: int, key: str, value: Any) -> Any:
        bindings = tuple(
            field
            for field in self.clan.optimizer_fields
            if field.optimizer_key == key and field.applies_to_group(group_index)
        )
        if not bindings:
            return self._stable_value(value)
        if any(field.tuple_index is None for field in bindings):
            return _TUNED_VALUE
        if not isinstance(value, tuple):
            raise TypeError(
                f"Optimizer field {key!r} must be a tuple for declared tuple bindings"
            )
        projected = list(value)
        for field in bindings:
            assert field.tuple_index is not None
            if field.tuple_index >= len(projected):
                raise IndexError(
                    f"Optimizer field {key!r} has length {len(projected)}, "
                    f"not declared index {field.tuple_index}"
                )
            projected[field.tuple_index] = _TUNED_VALUE
        return self._stable_value(tuple(projected))

    @staticmethod
    def _stable_value(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        if isinstance(value, tuple):
            return tuple(ClanDDPStrategy._stable_value(item) for item in value)
        return repr(value)

    def _apply_trial_optimizer_config(self) -> None:
        apply_optimizer_config(
            self.optimizers[0],
            self._trial_config,
            self.clan.optimizer_fields,
        )

    def _is_fresh_trial(self) -> bool:
        module = self.lightning_module
        if module is None or module.trainer is None:
            raise RuntimeError("Lightning module is not attached to a Trainer")
        checkpoint_path = module.trainer.ckpt_path
        if self.runtime.checkpoint_available and checkpoint_path is None:
            raise RuntimeError(
                "Ray supplied a trial checkpoint, but Lightning was started without "
                "ckpt_path. Use clan.tune_checkpoint_path() around Trainer.fit()."
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

    def _verify_runtime_ddp_invariants(self) -> None:
        wrapped = self.model
        if wrapped is None:
            raise RuntimeError("DDP model wrapper is unavailable after configuration")
        if getattr(wrapped, "broadcast_buffers", False):
            raise RuntimeError("ClanDDPStrategy failed to disable DDP buffer broadcasts")

    def _resolve_tune_runtime(self) -> ClanRuntime:
        try:
            from clan_based_tuning.ray.rendezvous import resolve_tune_runtime
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "Ray Tune is required unless ClanRuntime is supplied explicitly"
            ) from error
        return resolve_tune_runtime(self.clan)
