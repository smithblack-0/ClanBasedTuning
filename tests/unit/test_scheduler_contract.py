from types import SimpleNamespace

import pytest

from clan_based_tuning.ray.scheduler import ClanBasedTraining
from clan_based_tuning.spec import CLAN_MEMBER_ID_KEY, CLAN_METADATA_KEY


def test_scheduler_disables_buffered_results():
    assert ClanBasedTraining._supports_buffered_results is False


def test_scheduler_does_not_own_optimizer_mapping_schema():
    assert "optimizer_fields" not in ClanBasedTraining.__init__.__annotations__


@pytest.mark.requires_ray
@pytest.mark.parametrize("reserved_key", [CLAN_MEMBER_ID_KEY, CLAN_METADATA_KEY])
def test_scheduler_reserves_its_integration_keys(reserved_key):
    with pytest.raises(ValueError, match="Reserved integration keys"):
        ClanBasedTraining(
            population_size=2,
            metric="fitness",
            mode="min",
            hyperparam_mutations={reserved_key: [1, 2]},
        )


@pytest.mark.requires_ray
def test_scheduler_requires_integer_member_id_in_population_range():
    scheduler = ClanBasedTraining(population_size=2, metric="fitness", mode="min")

    with pytest.raises(RuntimeError, match="must define"):
        scheduler._member_id_from_config({})
    with pytest.raises(TypeError, match="must be an integer"):
        scheduler._member_id_from_config({CLAN_MEMBER_ID_KEY: True})
    with pytest.raises(ValueError, match="between 0 and 1"):
        scheduler._member_id_from_config({CLAN_MEMBER_ID_KEY: 2})


@pytest.mark.requires_ray
def test_scheduler_rejects_duplicate_explicit_member_assignment(monkeypatch):
    from ray.tune.schedulers import PopulationBasedTraining

    monkeypatch.setattr(PopulationBasedTraining, "on_trial_add", lambda *args: None)
    scheduler = ClanBasedTraining(population_size=3, metric="fitness", mode="min")
    resource_request = SimpleNamespace(bundles=[{"CPU": 1}], strategy="PACK")
    first = SimpleNamespace(
        trial_id="trial-a",
        config={CLAN_MEMBER_ID_KEY: 1},
        max_failures=0,
        placement_group_factory=resource_request,
    )
    duplicate = SimpleNamespace(
        trial_id="trial-b",
        config={CLAN_MEMBER_ID_KEY: 1},
        max_failures=0,
        placement_group_factory=resource_request,
    )

    scheduler.on_trial_add(None, first)

    with pytest.raises(RuntimeError, match="assigned to more than one trial"):
        scheduler.on_trial_add(None, duplicate)


@pytest.mark.requires_ray
def test_scheduler_rejects_member_id_change_after_registration(monkeypatch):
    from ray.tune.schedulers import PopulationBasedTraining

    monkeypatch.setattr(
        PopulationBasedTraining,
        "on_trial_result",
        lambda *args: "CONTINUE",
    )
    scheduler = ClanBasedTraining(population_size=2, metric="fitness", mode="min")
    scheduler._member_id_by_trial = {"trial-a": 0, "trial-b": 1}
    trial = SimpleNamespace(
        trial_id="trial-a",
        config={CLAN_MEMBER_ID_KEY: 1},
    )

    with pytest.raises(RuntimeError, match="changed its Clan member ID"):
        scheduler.on_trial_result(None, trial, {})


@pytest.mark.requires_ray
def test_scheduler_preserves_target_member_id_when_pbt_clones_config(monkeypatch):
    from ray.tune.schedulers import PopulationBasedTraining

    def cloned_config(*args):
        del args
        return {CLAN_MEMBER_ID_KEY: 0, "lr": 0.2}, {"lr": "* 2"}

    monkeypatch.setattr(PopulationBasedTraining, "_get_new_config", cloned_config)
    scheduler = ClanBasedTraining(population_size=2, metric="fitness", mode="min")
    scheduler._member_id_by_trial = {"target": 1}
    target = SimpleNamespace(trial_id="target")

    config, operations = scheduler._get_new_config(target, SimpleNamespace())

    assert config[CLAN_MEMBER_ID_KEY] == 1
    assert config["lr"] == 0.2
    assert operations == {"lr": "* 2"}
