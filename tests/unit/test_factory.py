from __future__ import annotations

from clan_based_tuning import ClanBase, ClanSpec, OptimizerField


def test_factory_reports_required_lightning_topology():
    clan = ClanBase(
        ClanSpec(
            population_size=3,
            optimizer_fields=(OptimizerField("lr", "lr"),),
            rendezvous_name="test-clan",
        )
    )

    assert clan.trainer_requirements == {
        "devices": 1,
        "num_nodes": 1,
        "enable_checkpointing": False,
    }
