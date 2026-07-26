import pytest

from clan_based_tuning.ray.scheduler import ClanBasedTraining


def test_scheduler_disables_buffered_results():
    assert ClanBasedTraining._supports_buffered_results is False


def test_scheduler_does_not_own_optimizer_mapping_schema():
    assert "optimizer_fields" not in ClanBasedTraining.__init__.__annotations__


@pytest.mark.requires_ray
def test_scheduler_rejects_ray_exploration_policy():
    with pytest.raises(TypeError, match="ClanController owns selection and mutation"):
        ClanBasedTraining(
            population_size=2,
            metric="fitness",
            mode="min",
            hyperparam_mutations={"lr": [0.1, 0.2]},
        )
