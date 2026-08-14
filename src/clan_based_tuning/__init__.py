"""Clan Tuning policy primitives and optional Ray/Lightning integration."""

from clan_based_tuning.controller import ClanController
from clan_based_tuning.evolution import MutationSpec

__all__ = [
    "ClanController",
    "MutationSpec",
]


def __getattr__(name: str):
    """Load the optional Ray/Lightning integration only when explicitly requested."""

    if name == "ClanScheduler":
        try:
            from clan_based_tuning.scheduler import ClanScheduler
        except ModuleNotFoundError as error:
            if error.name == "ray":
                raise ModuleNotFoundError(
                    'ClanScheduler requires: pip install "clan-based-tuning[ray]"'
                ) from error
            raise
        return ClanScheduler

    if name == "ClanDDPStrategy":
        try:
            from clan_based_tuning.lightning_strategy import ClanDDPStrategy
        except ModuleNotFoundError as error:
            if error.name in {"lightning", "lightning_utilities"}:
                raise ModuleNotFoundError(
                    'ClanDDPStrategy requires: pip install "clan-based-tuning[ray]"'
                ) from error
            raise
        return ClanDDPStrategy

    if name == "ClanTuneReportCallback":
        try:
            from clan_based_tuning.lightning_callback import ClanTuneReportCallback
        except ModuleNotFoundError as error:
            if error.name in {"lightning", "lightning_utilities", "ray"}:
                raise ModuleNotFoundError(
                    'ClanTuneReportCallback requires: pip install "clan-based-tuning[ray]"'
                ) from error
            raise
        return ClanTuneReportCallback

    raise AttributeError(name)
