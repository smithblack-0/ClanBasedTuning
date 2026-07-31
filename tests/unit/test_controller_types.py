import math

import pytest

from clan_based_tuning import MutationSpec
from clan_based_tuning.controller_types import (
    build_parent_genome_metadata,
    select_winner_id,
)


class FixedRandom:
    def __init__(self, displacement):
        self.displacement = displacement

    def gauss(self, mean, standard_deviation):
        return self.displacement


def test_mutation_spec_applies_linear_and_log_rules():
    linear = MutationSpec(
        standard_deviation=0.2,
        geometry="linear",
        minimum=0.0,
        maximum=3.0,
    )
    logarithmic = MutationSpec(
        standard_deviation=0.2,
        geometry="log",
        minimum=0.1,
        maximum=20.0,
    )

    assert linear.mutate(2.0, FixedRandom(0.3)) == 2.3
    assert linear.mutate(2.9, FixedRandom(0.3)) == 3.0
    assert logarithmic.mutate(2.0, FixedRandom(math.log(2.0))) == pytest.approx(4.0)


def test_unknown_mutation_geometry_crashes_when_used():
    mutation = MutationSpec(
        standard_deviation=0.2,
        geometry="quadratic",
        minimum=0.0,
        maximum=3.0,
    )

    with pytest.raises(ValueError, match="unknown mutation geometry"):
        mutation.mutate(2.0, FixedRandom(0.3))


def test_shared_selection_rule_matches_worker_and_scheduler_needs():
    assert select_winner_id([4.0, 1.0, 2.0], "min") == 1
    assert select_winner_id([5.0, 5.0, 2.0], "max") == 0


def test_parent_genome_metadata_namespaces_checkpoint_provenance():
    genome = {"lr": 0.004, "weight_decay": 0.08}

    metadata = build_parent_genome_metadata(
        round_index=7,
        source_member_id=2,
        source_trial_id="trial_00002",
        genome=genome,
    )
    genome["lr"] = 9.0

    assert metadata == {
        "clan_based_tuning": {
            "schema_version": 1,
            "round_index": 7,
            "source_member_id": 2,
            "source_trial_id": "trial_00002",
            "parent_genome": {"lr": 0.004, "weight_decay": 0.08},
        }
    }
