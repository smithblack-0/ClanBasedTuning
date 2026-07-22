"""Map Ray Tune configuration values onto a trial's live optimizer.

The mapping is deliberately explicit. Ray owns the trial configuration and
checkpoint inheritance; this module defines the small adapter that reapplies the
target trial's optimizer values after Lightning restores the source checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from torch.optim import Optimizer


@dataclass(frozen=True, slots=True)
class OptimizerField:
    """Bind one top-level Tune config key to one optimizer param-group field.

    ``tuple_index`` supports fields such as ``betas[0]`` without giving the
    integration arbitrary mutation access to optimizer internals. By default the
    value is applied to every parameter group; ``group_indices`` can restrict the
    binding when a model deliberately uses heterogeneous groups.
    """

    config_key: str
    optimizer_key: str
    tuple_index: int | None = None
    group_indices: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if not self.config_key:
            raise ValueError("config_key must be non-empty")
        if not self.optimizer_key:
            raise ValueError("optimizer_key must be non-empty")
        if self.tuple_index is not None and self.tuple_index < 0:
            raise ValueError("tuple_index must be non-negative")
        if self.group_indices is not None:
            if not self.group_indices:
                raise ValueError("group_indices must be non-empty when supplied")
            if len(set(self.group_indices)) != len(self.group_indices):
                raise ValueError("group_indices must not contain duplicates")
            if any(index < 0 for index in self.group_indices):
                raise ValueError("group_indices must be non-negative")

    def applies_to_group(self, group_index: int) -> bool:
        """Return whether this gene controls the selected parameter group."""

        return self.group_indices is None or group_index in self.group_indices

    def overlaps(self, other: OptimizerField) -> bool:
        """Return whether two bindings can target at least one common group."""

        if self.group_indices is None or other.group_indices is None:
            return True
        return bool(set(self.group_indices).intersection(other.group_indices))

    def apply(self, optimizer: Optimizer, config: dict[str, Any]) -> None:
        """Apply this binding, failing if either side violates the contract."""

        try:
            value = config[self.config_key]
        except KeyError as error:
            raise KeyError(
                f"Tune config is missing optimizer field {self.config_key!r}"
            ) from error

        indices = self.group_indices or tuple(range(len(optimizer.param_groups)))
        for group_index in indices:
            try:
                group = optimizer.param_groups[group_index]
            except IndexError as error:
                raise IndexError(
                    f"Optimizer has no parameter group {group_index} for "
                    f"binding {self.config_key!r}"
                ) from error
            if self.optimizer_key not in group:
                raise KeyError(
                    f"Optimizer parameter group {group_index} has no field "
                    f"{self.optimizer_key!r}"
                )

            if self.tuple_index is None:
                group[self.optimizer_key] = value
                continue

            current = group[self.optimizer_key]
            if not isinstance(current, tuple):
                raise TypeError(
                    f"Optimizer field {self.optimizer_key!r} must be a tuple to apply "
                    f"tuple index {self.tuple_index}"
                )
            if self.tuple_index >= len(current):
                raise IndexError(
                    f"Optimizer field {self.optimizer_key!r} has length {len(current)}, "
                    f"not index {self.tuple_index}"
                )
            updated = list(current)
            updated[self.tuple_index] = value
            group[self.optimizer_key] = tuple(updated)


def apply_optimizer_config(
    optimizer: Optimizer,
    config: dict[str, Any],
    fields: tuple[OptimizerField, ...],
) -> None:
    """Apply all declared optimizer genes to one live optimizer."""

    for field in fields:
        field.apply(optimizer, config)
