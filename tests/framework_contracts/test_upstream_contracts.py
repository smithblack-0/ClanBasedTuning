"""Sentinels for upstream implementation details the integration relies on.

These tests are intentionally narrow. They should fail when an upstream change
requires us to re-audit the integration rather than silently preserving an old
assumption.
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import pytest
from lightning.pytorch.strategies import DDPStrategy, Strategy
from lightning.pytorch.trainer.connectors.data_connector import _DataConnector


@pytest.mark.framework_contract
def test_lightning_ddp_forwards_divergence_controls():
    strategy = DDPStrategy(broadcast_buffers=False, init_sync=False)
    assert strategy._ddp_kwargs["broadcast_buffers"] is False
    assert strategy._ddp_kwargs["init_sync"] is False


@pytest.mark.framework_contract
def test_lightning_base_checkpoint_write_is_global_zero_gated():
    source = textwrap.dedent(inspect.getsource(Strategy.save_checkpoint))
    tree = ast.parse(source)
    conditions = [node.test for node in ast.walk(tree) if isinstance(node, ast.If)]
    assert any(
        isinstance(condition, ast.Attribute)
        and condition.attr == "is_global_zero"
        for condition in conditions
    )


@pytest.mark.framework_contract
@pytest.mark.requires_ray
def test_ray_pbt_exploit_keeps_target_trial_and_replaces_its_continuation():
    ray = pytest.importorskip("ray")
    del ray
    from ray.tune.schedulers.pbt import PopulationBasedTraining

    source = textwrap.dedent(inspect.getsource(PopulationBasedTraining._exploit))
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    # The integration depends on PBT retaining the target Trial object while
    # replacing its config and checkpoint-backed continuation.
    assert "pause_trial" in called_attributes
    assert "set_config" in called_attributes
    assert "_get_new_config" in called_attributes
    assert "copy" in called_attributes


@pytest.mark.framework_contract
def test_lightning_preserves_user_distributed_sampler_instances():
    source = textwrap.dedent(inspect.getsource(_DataConnector._requires_distributed_sampler))
    tree = ast.parse(source)
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "isinstance"
        and any(
            isinstance(argument, ast.Name) and argument.id == "DistributedSampler"
            for argument in node.args
        )
        for node in ast.walk(tree)
    )
