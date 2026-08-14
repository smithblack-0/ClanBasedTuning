"""Public package-surface contract for the ordinary user integration objects."""

import clan_based_tuning


def test_package_root_exports_the_complete_user_surface() -> None:
    """A normal package import exposes the scheduler, strategy, and reporting callback."""

    assert clan_based_tuning.__all__ == [
        "ClanDDPStrategy",
        "ClanScheduler",
        "ClanTuneReportCallback",
    ]
    assert clan_based_tuning.ClanScheduler is not None
    assert clan_based_tuning.ClanDDPStrategy is not None
    assert clan_based_tuning.ClanTuneReportCallback is not None
