from __future__ import annotations

import pytest
import torch

from clan_based_tuning import OptimizerField
from clan_based_tuning.optimizer import apply_optimizer_config


def test_optimizer_fields_apply_scalars_and_tuple_elements():
    parameter = torch.nn.Parameter(torch.tensor(1.0))
    optimizer = torch.optim.AdamW([parameter], lr=9.0, betas=(0.9, 0.999))

    apply_optimizer_config(
        optimizer,
        {"lr": 0.02, "beta1": 0.8},
        (
            OptimizerField("lr", "lr"),
            OptimizerField("beta1", "betas", tuple_index=0),
        ),
    )

    assert optimizer.param_groups[0]["lr"] == pytest.approx(0.02)
    assert optimizer.param_groups[0]["betas"] == pytest.approx((0.8, 0.999))


def test_optimizer_field_missing_config_crashes():
    parameter = torch.nn.Parameter(torch.tensor(1.0))
    optimizer = torch.optim.SGD([parameter], lr=0.1)

    with pytest.raises(KeyError, match="missing optimizer field"):
        OptimizerField("lr", "lr").apply(optimizer, {})


def test_optimizer_field_missing_runtime_field_crashes():
    parameter = torch.nn.Parameter(torch.tensor(1.0))
    optimizer = torch.optim.SGD([parameter], lr=0.1)

    with pytest.raises(KeyError, match="has no field"):
        OptimizerField("alpha", "alpha").apply(optimizer, {"alpha": 1.0})
