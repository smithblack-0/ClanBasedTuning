"""Ray checkpoint contract for winner-side genome provenance."""

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]
pytest.importorskip("ray")

from ray.train import Checkpoint  # noqa: E402

from clan_based_tuning import ClanController  # noqa: E402


def test_selected_controller_updates_only_the_checkpoint_sidecar(tmp_path):
    payload_path = tmp_path / "training.ckpt"
    payload = b"opaque-lightning-checkpoint"
    payload_path.write_bytes(payload)

    controller = ClanController(
        member_id=1,
        population_size=2,
        mode="min",
        genome={"lr": 0.003, "weight_decay": 0.1},
        exchange_fitness=lambda local_fitness: [2.0, local_fitness],
    )
    controller.set_fitness(1.0)
    assert controller.should_save_checkpoint() is True

    checkpoint = Checkpoint.from_directory(tmp_path)
    checkpoint.set_metadata({"lightning": {"format": "ckpt"}})

    returned = controller.save_genome(checkpoint)

    assert returned is checkpoint
    assert payload_path.read_bytes() == payload
    assert checkpoint.get_metadata() == {
        "lightning": {"format": "ckpt"},
        "clan_based_tuning": {
            "schema_version": 1,
            "member_id": 1,
            "genome": {"lr": 0.003, "weight_decay": 0.1},
        },
    }
