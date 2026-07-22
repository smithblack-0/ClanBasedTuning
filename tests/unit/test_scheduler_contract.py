import pytest

from clan_based_tuning.ray.scheduler import ClanBasedTraining
from clan_based_tuning.spec import CLAN_METADATA_KEY


def test_scheduler_disables_buffered_results():
    assert ClanBasedTraining._supports_buffered_results is False


def test_scheduler_does_not_own_optimizer_mapping_schema():
    assert "optimizer_fields" not in ClanBasedTraining.__init__.__annotations__


def test_scheduler_reserves_only_its_integration_metadata_key():
    with pytest.raises(ValueError, match="reserved integration metadata"):
        ClanBasedTraining(
            population_size=2,
            metric="fitness",
            mode="min",
            hyperparam_mutations={CLAN_METADATA_KEY: [1, 2]},
        )
