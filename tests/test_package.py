"""Package-level public-surface checks."""


def test_declared_package_exports_are_bound():
    """Pre: package declares __all__. Post: every declared export resolves."""
    import clan_based_tuning

    assert clan_based_tuning.__name__ == "clan_based_tuning"
    for name in clan_based_tuning.__all__:
        assert getattr(clan_based_tuning, name) is not None
