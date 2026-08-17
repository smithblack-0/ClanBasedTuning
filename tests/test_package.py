"""Public package-surface contract for the three ordinary user integration objects.

The contract protects which objects CBT asks users to compose, not the source-order formatting
of ``__all__``. Keeping that distinction avoids turning harmless export reordering into an API
failure while still rejecting accidental additions/removals.
"""

import clan_based_tuning


def test_package_root_exports_the_complete_user_surface() -> None:
    """Expose exactly scheduler, strategy, and reporting callback from the package root."""

    assert set(clan_based_tuning.__all__) == {
        "ClanDDPStrategy",
        "ClanScheduler",
        "ClanTuneReportCallback",
    }
    assert clan_based_tuning.ClanScheduler is not None
    assert clan_based_tuning.ClanDDPStrategy is not None
    assert clan_based_tuning.ClanTuneReportCallback is not None
