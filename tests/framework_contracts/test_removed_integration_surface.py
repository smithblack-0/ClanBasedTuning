"""Boundary contract for the removed proof-of-concept Ray integration."""

import pytest


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_installing_ray_does_not_restore_an_unaccepted_package_surface():
    """Ray may be installed for research without activating removed package APIs."""

    import ray

    import clan_based_tuning

    assert ray.__name__ == "ray"
    assert clan_based_tuning.__all__ == [
        "ClanController",
        "ClanRound",
        "MutationSpec",
    ]
    assert not hasattr(clan_based_tuning, "ClanBasedTraining")
