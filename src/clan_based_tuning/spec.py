"""Shared immutable contract between the Ray scheduler and Lightning strategy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from clan_based_tuning.optimizer import OptimizerField

CLAN_METADATA_KEY = "__clan_based_training__"
CLAN_PROTOCOL_VERSION = 1


@dataclass(frozen=True, slots=True)
class ClanSpec:
    """Describe one fixed synchronous clan.

    The specification contains only facts both framework adapters must agree on.
    It does not own mutable scheduler state, trial state, or a Ray actor handle.

    Ray trial configuration carries a serialized copy of this specification.
    That copy is authoritative on experiment restore, so a reconstructed user
    frontend cannot accidentally point restored trials at a new rendezvous.
    """

    population_size: int
    optimizer_fields: tuple[OptimizerField, ...]
    rendezvous_name: str = field(default_factory=lambda: f"clan-rendezvous-{uuid4().hex}")
    rendezvous_namespace: str = "clan-based-tuning"
    rendezvous_timeout_s: float = 300.0
    rendezvous_poll_interval_s: float = 0.1

    def __post_init__(self) -> None:
        if self.population_size < 2:
            raise ValueError("population_size must be at least 2")
        if not self.optimizer_fields:
            raise ValueError("At least one optimizer field must be declared")
        config_keys = [field.config_key for field in self.optimizer_fields]
        if len(set(config_keys)) != len(config_keys):
            raise ValueError("Optimizer config keys must be unique")
        if CLAN_METADATA_KEY in config_keys:
            raise ValueError(f"{CLAN_METADATA_KEY!r} is reserved for clan metadata")
        for index, field in enumerate(self.optimizer_fields):
            for other in self.optimizer_fields[index + 1 :]:
                if field.optimizer_key != other.optimizer_key or not field.overlaps(other):
                    continue
                if field.tuple_index is None or other.tuple_index is None:
                    raise ValueError(
                        "Overlapping optimizer bindings cannot combine whole-field and "
                        f"tuple-element control for {field.optimizer_key!r}"
                    )
                if field.tuple_index == other.tuple_index:
                    raise ValueError(
                        "Optimizer bindings cannot control the same tuple element on "
                        f"overlapping groups: {field.optimizer_key}[{field.tuple_index}]"
                    )
        if not self.rendezvous_name:
            raise ValueError("rendezvous_name must be non-empty")
        if not self.rendezvous_namespace:
            raise ValueError("rendezvous_namespace must be non-empty")
        if self.rendezvous_timeout_s <= 0:
            raise ValueError("rendezvous_timeout_s must be positive")
        if self.rendezvous_poll_interval_s <= 0:
            raise ValueError("rendezvous_poll_interval_s must be positive")

    @property
    def optimizer_config_keys(self) -> frozenset[str]:
        """Return the exact Tune config keys the clan scheduler may mutate."""

        return frozenset(field.config_key for field in self.optimizer_fields)

    @property
    def compatibility_signature(self) -> tuple[int, tuple[OptimizerField, ...]]:
        """Return scientific structure that must match reconstructed frontends."""

        return self.population_size, self.optimizer_fields

    def to_trial_metadata(self) -> dict[str, Any]:
        """Serialize the durable integration contract into a Tune trial config."""

        return {
            "protocol_version": CLAN_PROTOCOL_VERSION,
            "population_size": self.population_size,
            "optimizer_fields": [
                {
                    "config_key": field.config_key,
                    "optimizer_key": field.optimizer_key,
                    "tuple_index": field.tuple_index,
                    "group_indices": (
                        None
                        if field.group_indices is None
                        else list(field.group_indices)
                    ),
                }
                for field in self.optimizer_fields
            ],
            "rendezvous_name": self.rendezvous_name,
            "rendezvous_namespace": self.rendezvous_namespace,
            "rendezvous_timeout_s": self.rendezvous_timeout_s,
            "rendezvous_poll_interval_s": self.rendezvous_poll_interval_s,
        }

    @classmethod
    def from_trial_metadata(cls, metadata: Mapping[str, Any]) -> ClanSpec:
        """Reconstruct the authoritative clan contract from trial metadata."""

        version = metadata["protocol_version"]
        if version != CLAN_PROTOCOL_VERSION:
            raise RuntimeError(
                "Unsupported Clan Based Training protocol version: "
                f"expected {CLAN_PROTOCOL_VERSION}, got {version}"
            )
        fields = tuple(
            OptimizerField(
                config_key=field["config_key"],
                optimizer_key=field["optimizer_key"],
                tuple_index=field["tuple_index"],
                group_indices=(
                    None
                    if field["group_indices"] is None
                    else tuple(field["group_indices"])
                ),
            )
            for field in metadata["optimizer_fields"]
        )
        return cls(
            population_size=int(metadata["population_size"]),
            optimizer_fields=fields,
            rendezvous_name=str(metadata["rendezvous_name"]),
            rendezvous_namespace=str(metadata["rendezvous_namespace"]),
            rendezvous_timeout_s=float(metadata["rendezvous_timeout_s"]),
            rendezvous_poll_interval_s=float(metadata["rendezvous_poll_interval_s"]),
        )

    def bind_trial_config(self, config: dict[str, Any]) -> None:
        """Insert or verify durable metadata in one mutable Tune trial config."""

        metadata = config.get(CLAN_METADATA_KEY)
        expected = self.to_trial_metadata()
        if metadata is None:
            config[CLAN_METADATA_KEY] = expected
            return
        if metadata != expected:
            raise RuntimeError(
                "Tune trial contains clan metadata that disagrees with its scheduler"
            )

    def resolve_trial_config(self, config: Mapping[str, Any]) -> ClanSpec:
        """Use persisted metadata when present and verify scientific compatibility."""

        metadata = config.get(CLAN_METADATA_KEY)
        if metadata is None:
            return self
        restored = type(self).from_trial_metadata(metadata)
        if restored.compatibility_signature != self.compatibility_signature:
            raise RuntimeError(
                "Restored Tune trial clan structure disagrees with the current frontend"
            )
        return restored
