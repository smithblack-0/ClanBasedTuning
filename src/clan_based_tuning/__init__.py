"""Clan Tuning policy primitives and optional Ray/Lightning integration."""

from clan_based_tuning.controller import ClanController
from clan_based_tuning.evolution import MutationSpec

__all__ = [
    "ClanController",
    "MutationSpec",
    "ClanScheduler",
    "ClanDDPStrategy",
    "ClanTuneReportCallback",
]


def __getattr__(name: str):
    """Load the heavy Ray/Lightning surface only when the integration is requested."""

    if name == "ClanScheduler":
        try:
            from clan_based_tuning.scheduler import ClanScheduler
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                'ClanScheduler requires: pip install "clan-based-tuning[ray]"'
            ) from error
        return ClanScheduler
    if name == "ClanDDPStrategy":
        try:
            from clan_based_tuning.lightning_strategy import ClanDDPStrategy
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                'ClanDDPStrategy requires: pip install "clan-based-tuning[ray]"'
            ) from error
        return ClanDDPStrategy
    if name == "ClanTuneReportCallback":
        try:
            from clan_based_tuning.lightning_callback import ClanTuneReportCallback
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                'ClanTuneReportCallback requires: pip install "clan-based-tuning[ray]"'
            ) from error
        return ClanTuneReportCallback
    raise AttributeError(name)
