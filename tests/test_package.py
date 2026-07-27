"""Package-level public-surface checks."""


def test_package_exports_only_the_accepted_milestone_2_surface():
    """The package root exposes the controller subsystem and no old integration API."""

    import clan_based_tuning

    assert clan_based_tuning.__name__ == "clan_based_tuning"
    assert clan_based_tuning.__all__ == [
        "ClanController",
        "ClanRound",
        "MutationSpec",
    ]
    for name in clan_based_tuning.__all__:
        assert getattr(clan_based_tuning, name) is not None

    removed_names = {
        "ClanBasedTraining",
        "ClanDDPStrategy",
        "ClanLightningEnvironment",
        "ClanLightningPlugins",
        "apply_optimizer_strategy",
        "make_clan_lightning_plugins",
        "prepare_clan_trainer",
        "replicated_sampler",
        "tune_checkpoint_path",
    }
    assert not any(hasattr(clan_based_tuning, name) for name in removed_names)
