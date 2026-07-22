from __future__ import annotations

import pytest

from clan_based_tuning.spec import (
    CLAN_METADATA_KEY,
    _ClanMetadata,
    _metadata_from_trial_config,
)


def test_internal_metadata_round_trips_through_trial_config():
    original = _ClanMetadata(
        population_size=3,
        rendezvous_name="persisted-clan",
        rendezvous_timeout_s=42.0,
    )
    config: dict[str, object] = {}
    original.bind_trial_config(config)

    assert _metadata_from_trial_config(config) == original


def test_missing_metadata_explains_scheduler_boundary():
    with pytest.raises(RuntimeError, match="Construct the Tune run with ClanBasedTraining"):
        _metadata_from_trial_config({})


def test_binding_rejects_a_different_persisted_clan():
    config = {
        CLAN_METADATA_KEY: _ClanMetadata(
            population_size=2,
            rendezvous_name="first",
        ).to_trial_metadata()
    }

    with pytest.raises(RuntimeError, match="disagrees with its scheduler"):
        _ClanMetadata(population_size=2, rendezvous_name="second").bind_trial_config(config)
