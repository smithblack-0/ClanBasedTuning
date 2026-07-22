from __future__ import annotations

from clan_based_tuning import ClanSpec, OptimizerField
from clan_based_tuning.ray.scheduler import ClanBasedTraining


def test_scheduler_disables_buffered_results():
    assert ClanBasedTraining._supports_buffered_results is False


def test_scheduler_adopts_persisted_rendezvous_metadata_on_restore():
    persisted = ClanSpec(
        population_size=2,
        optimizer_fields=(OptimizerField("lr", "lr"),),
        rendezvous_name="persisted-clan",
    )
    config: dict[str, object] = {}
    persisted.bind_trial_config(config)

    reconstructed = ClanSpec(
        population_size=2,
        optimizer_fields=persisted.optimizer_fields,
        rendezvous_name="new-frontend-clan",
    )
    scheduler = object.__new__(ClanBasedTraining)
    scheduler.clan = reconstructed
    scheduler._member_ranks = {}

    scheduler._resolve_or_bind_clan(config)

    assert scheduler.clan == persisted
