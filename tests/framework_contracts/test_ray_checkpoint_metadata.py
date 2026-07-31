"""Ray checkpoint contract for scheduler-owned parent-genome provenance."""

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
pytest.importorskip("ray")

from ray.train import Checkpoint  # noqa: E402

from clan_based_tuning.controller_types import (  # noqa: E402
    attach_parent_genome_metadata,
)


def test_parent_genome_metadata_updates_only_the_checkpoint_sidecar(tmp_path):
    """The scheduler can bind provenance without opening the Lightning payload."""

    payload_path = tmp_path / "training.ckpt"
    payload = b"opaque-lightning-checkpoint"
    payload_path.write_bytes(payload)

    checkpoint = Checkpoint.from_directory(tmp_path)
    checkpoint.set_metadata({"lightning": {"format": "ckpt"}})

    returned = attach_parent_genome_metadata(
        checkpoint,
        round_index=7,
        source_member_id=2,
        source_trial_id="trial-b",
        genome={"lr": 0.003, "weight_decay": 0.1},
    )

    assert returned is checkpoint
    assert payload_path.read_bytes() == payload
    assert checkpoint.get_metadata() == {
        "lightning": {"format": "ckpt"},
        "clan_based_tuning": {
            "schema_version": 1,
            "round_index": 7,
            "source_member_id": 2,
            "source_trial_id": "trial-b",
            "parent_genome": {"lr": 0.003, "weight_decay": 0.1},
        },
    }
