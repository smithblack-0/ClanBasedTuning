"""Package-level public-surface checks."""


def test_package_exports_the_worker_controller_and_mutation_spec():
    """The package root exposes the active CBT surface and no rejected lifecycle API."""

    import clan_based_tuning

    assert clan_based_tuning.__name__ == "clan_based_tuning"
    assert clan_based_tuning.__all__ == [
        "ClanController",
        "MutationSpec",
    ]
    for name in clan_based_tuning.__all__:
        assert getattr(clan_based_tuning, name) is not None

    removed_names = {
        "ClanRound",
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
