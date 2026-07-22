from __future__ import annotations

import pytest

from clan_based_tuning import ClanSpec, OptimizerField


def test_clan_spec_exposes_declared_optimizer_keys():
    spec = ClanSpec(
        population_size=4,
        optimizer_fields=(
            OptimizerField("lr", "lr"),
            OptimizerField("weight_decay", "weight_decay"),
        ),
        rendezvous_name="test-clan",
    )

    assert spec.optimizer_config_keys == frozenset({"lr", "weight_decay"})


def test_clan_spec_rejects_duplicate_config_keys():
    with pytest.raises(ValueError, match="must be unique"):
        ClanSpec(
            population_size=2,
            optimizer_fields=(
                OptimizerField("lr", "lr"),
                OptimizerField("lr", "other"),
            ),
            rendezvous_name="test-clan",
        )


def test_clan_spec_trial_metadata_round_trips_and_survives_frontend_reconstruction():
    original = ClanSpec(
        population_size=3,
        optimizer_fields=(
            OptimizerField("lr", "lr"),
            OptimizerField("beta1", "betas", tuple_index=0, group_indices=(0, 2)),
        ),
        rendezvous_name="persisted-clan",
        rendezvous_timeout_s=42.0,
    )
    config: dict[str, object] = {}
    original.bind_trial_config(config)

    reconstructed_frontend = ClanSpec(
        population_size=3,
        optimizer_fields=original.optimizer_fields,
        rendezvous_name="new-random-clan",
    )
    restored = reconstructed_frontend.resolve_trial_config(config)

    assert restored == original
    assert restored.rendezvous_name == "persisted-clan"


def test_clan_spec_rejects_incompatible_restored_structure():
    original = ClanSpec(
        population_size=2,
        optimizer_fields=(OptimizerField("lr", "lr"),),
        rendezvous_name="persisted-clan",
    )
    config: dict[str, object] = {}
    original.bind_trial_config(config)

    incompatible = ClanSpec(
        population_size=3,
        optimizer_fields=(OptimizerField("lr", "lr"),),
        rendezvous_name="new-clan",
    )
    with pytest.raises(RuntimeError, match="structure disagrees"):
        incompatible.resolve_trial_config(config)


def test_clan_spec_rejects_overlapping_optimizer_targets():
    with pytest.raises(ValueError, match="same tuple element"):
        ClanSpec(
            population_size=2,
            optimizer_fields=(
                OptimizerField("beta1_a", "betas", tuple_index=0),
                OptimizerField("beta1_b", "betas", tuple_index=0),
            ),
            rendezvous_name="test-clan",
        )

    with pytest.raises(ValueError, match="whole-field and tuple-element"):
        ClanSpec(
            population_size=2,
            optimizer_fields=(
                OptimizerField("betas", "betas"),
                OptimizerField("beta1", "betas", tuple_index=0),
            ),
            rendezvous_name="test-clan",
        )
