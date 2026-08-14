"""Opt-in physical multi-node qualification for the public Clan function path.

This contract connects to an already-running Ray cluster and requires two CPU members to land
on different physical nodes. The cluster should expose one schedulable CPU per intended test
node (or otherwise constrain placement) so a successful run actually proves cross-node DDP.
"""

import os
from pathlib import Path

import pytest
import ray
from ray import tune

from tests.support.tiny_mlp import (
    build_tiny_scheduler,
    tiny_param_space,
    tiny_tune_config,
    train_tiny_mlp_member,
)

pytestmark = [
    pytest.mark.framework_contract,
    pytest.mark.requires_ray,
    pytest.mark.requires_multi_node,
]


def test_two_members_train_on_distinct_physical_nodes(tmp_path: Path) -> None:
    """Two Ray-cluster nodes join one framework-managed GLOO Clan world."""

    if "CLAN_RUN_MULTI_NODE" not in os.environ or os.environ["CLAN_RUN_MULTI_NODE"] != "1":
        pytest.skip("set CLAN_RUN_MULTI_NODE=1 after starting the qualification Ray cluster")

    address = os.environ.get("CLAN_TEST_RAY_ADDRESS", "auto")
    ray.shutdown()
    ray.init(address=address, log_to_driver=False)
    try:
        alive_nodes = [node for node in ray.nodes() if node["Alive"]]
        assert len(alive_nodes) >= 2, (
            "multi-node qualification requires at least two live Ray nodes"
        )
        assert ray.cluster_resources()["CPU"] >= 2

        results = tune.Tuner(
            tune.with_resources(train_tiny_mlp_member, {"cpu": 1}),
            param_space=tiny_param_space(accelerator="cpu", ddp_timeout_s=60.0),
            tune_config=tiny_tune_config(build_tiny_scheduler(join_timeout_s=60.0)),
            run_config=tune.RunConfig(
                name="tiny-mlp-multi-node-contract",
                storage_path=str(tmp_path),
                stop={"training_iteration": 2},
                verbose=0,
            ),
        ).fit()
    finally:
        ray.shutdown()

    assert len(results) == 2
    assert all(result.error is None for result in results)
    node_fingerprints = {result.metrics["node_fingerprint"] for result in results}
    assert len(node_fingerprints) == 2, (
        "both members landed on one physical node; constrain Ray resources and rerun"
    )
    assert all(result.metrics["world_size_seen"] == pytest.approx(2.0) for result in results)
