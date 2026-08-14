"""Clan Tuning integration for Ray Tune, Lightning, and PyTorch."""

__all__ = [
    "ClanDDPStrategy",
    "ClanScheduler",
    "ClanTuneReportCallback",
]


def __getattr__(name: str):
    """Load optional Ray/Lightning integration objects only when requested."""

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
            if error.name in {"lightning", "lightning_utilities", "ray"}:
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
