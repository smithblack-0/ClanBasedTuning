"""Private durable metadata shared by the Ray and Lightning integrations."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

CLAN_METADATA_KEY = "__clan_based_training__"
CLAN_PROTOCOL_VERSION = 1


@dataclass(frozen=True, slots=True)
class _ClanMetadata:
    """Identify one fixed clan across Tune scheduling and actor restoration.

    This record contains only integration facts needed to rebuild the external
    process group. Optimizer interpretation deliberately does not belong here:
    Ray's current trial config is authoritative, and the user-supplied optimizer
    strategy decides how that config applies to live optimizers.
    """

    population_size: int
    rendezvous_name: str = field(default_factory=lambda: f"clan-rendezvous-{uuid4().hex}")
    rendezvous_namespace: str = "clan-based-tuning"
    rendezvous_timeout_s: float = 300.0
    rendezvous_poll_interval_s: float = 0.1

    def __post_init__(self) -> None:
        if self.population_size < 2:
            raise ValueError("population_size must be at least 2")
        if not self.rendezvous_name:
            raise ValueError("rendezvous_name must be non-empty")
        if not self.rendezvous_namespace:
            raise ValueError("rendezvous_namespace must be non-empty")
        if self.rendezvous_timeout_s <= 0:
            raise ValueError("rendezvous_timeout_s must be positive")
        if self.rendezvous_poll_interval_s <= 0:
            raise ValueError("rendezvous_poll_interval_s must be positive")

    def to_trial_metadata(self) -> dict[str, Any]:
        return {
            "protocol_version": CLAN_PROTOCOL_VERSION,
            **asdict(self),
        }

    @classmethod
    def from_trial_metadata(cls, metadata: Mapping[str, Any]) -> _ClanMetadata:
        version = metadata["protocol_version"]
        if version != CLAN_PROTOCOL_VERSION:
            raise RuntimeError(
                "Unsupported Clan Based Training protocol version: "
                f"expected {CLAN_PROTOCOL_VERSION}, got {version}"
            )
        return cls(
            population_size=int(metadata["population_size"]),
            rendezvous_name=str(metadata["rendezvous_name"]),
            rendezvous_namespace=str(metadata["rendezvous_namespace"]),
            rendezvous_timeout_s=float(metadata["rendezvous_timeout_s"]),
            rendezvous_poll_interval_s=float(metadata["rendezvous_poll_interval_s"]),
        )

    def bind_trial_config(self, config: MutableMapping[str, Any]) -> None:
        """Insert the metadata once, or verify the persisted authority on restore."""

        expected = self.to_trial_metadata()
        if CLAN_METADATA_KEY not in config:
            config[CLAN_METADATA_KEY] = expected
        elif config[CLAN_METADATA_KEY] != expected:
            raise RuntimeError(
                "Tune trial contains clan metadata that disagrees with its scheduler"
            )


def _metadata_from_trial_config(config: Mapping[str, Any]) -> _ClanMetadata:
    """Resolve the integration metadata installed by ``ClanBasedTraining``."""

    try:
        metadata = config[CLAN_METADATA_KEY]
    except KeyError as error:
        raise RuntimeError(
            "Tune trial config has no Clan Based Training metadata. Construct the "
            "Tune run with ClanBasedTraining before creating Lightning plugins."
        ) from error
    if not isinstance(metadata, Mapping):
        raise TypeError(f"{CLAN_METADATA_KEY!r} must contain a mapping")
    return _ClanMetadata.from_trial_metadata(metadata)
