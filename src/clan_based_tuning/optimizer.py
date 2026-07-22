"""Optimizer reconciliation after Ray PBT checkpoint restoration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from torch.optim import Optimizer


class OptimizerStrategy(Protocol):
    """Apply the current Ray trial config to Lightning's live optimizers."""

    def __call__(
        self,
        optimizers: Sequence[Optimizer],
        config: Mapping[str, Any],
    ) -> None: ...


def apply_optimizer_strategy(
    optimizers: Sequence[Optimizer],
    config: Mapping[str, Any],
) -> None:
    """Apply matching top-level config values to one optimizer parameter group.

    This intentionally narrow default handles the common Ray PBT pattern without
    claiming to infer arbitrary optimizer structure. Supply another
    ``OptimizerStrategy`` when using multiple optimizers, multiple parameter
    groups, aliases, tuple elements, or transformed values.
    """

    if len(optimizers) != 1:
        raise ValueError(
            "The default optimizer strategy supports exactly one optimizer. "
            "Supply apply_optimizer_strategy=... for another layout."
        )
    optimizer = optimizers[0]
    if len(optimizer.param_groups) != 1:
        raise ValueError(
            "The default optimizer strategy supports exactly one parameter group. "
            "Supply apply_optimizer_strategy=... for another layout."
        )

    group = optimizer.param_groups[0]
    for name, value in config.items():
        if name != "params" and name in group:
            group[name] = value
