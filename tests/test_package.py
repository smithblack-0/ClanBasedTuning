"""Package-level environment checks."""


def test_package_imports() -> None:
    import clan_based_tuning

    assert clan_based_tuning.__name__ == "clan_based_tuning"
