"""Public package-surface checks."""


def test_package_root_names_the_actual_user_integration_surface():
    import clan_based_tuning

    assert clan_based_tuning.__all__ == [
        "ClanDDPStrategy",
        "ClanScheduler",
        "ClanTuneReportCallback",
    ]

    # Internal policy objects and application helpers are not ordinary-user API.
    assert "ClanController" not in clan_based_tuning.__all__
    assert "MutationSpec" not in clan_based_tuning.__all__
    assert not hasattr(clan_based_tuning, "apply_genome")
