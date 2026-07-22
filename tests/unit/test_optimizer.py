from __future__ import annotations

import pytest
import torch

from clan_based_tuning import apply_optimizer_strategy


def test_default_strategy_applies_matching_config_fields_only():
    parameter = torch.nn.Parameter(torch.tensor(1.0))
    optimizer = torch.optim.AdamW([parameter], lr=9.0, weight_decay=0.5, betas=(0.9, 0.999))

    apply_optimizer_strategy(
        [optimizer],
        {"lr": 0.02, "weight_decay": 0.01, "batch_size": 128},
    )

    assert optimizer.param_groups[0]["lr"] == pytest.approx(0.02)
    assert optimizer.param_groups[0]["weight_decay"] == pytest.approx(0.01)
    assert optimizer.param_groups[0]["betas"] == pytest.approx((0.9, 0.999))
    assert "batch_size" not in optimizer.param_groups[0]


def test_default_strategy_rejects_multiple_optimizers():
    first = torch.optim.SGD([torch.nn.Parameter(torch.tensor(1.0))], lr=0.1)
    second = torch.optim.SGD([torch.nn.Parameter(torch.tensor(2.0))], lr=0.1)

    with pytest.raises(ValueError, match="exactly one optimizer"):
        apply_optimizer_strategy([first, second], {"lr": 0.2})


def test_default_strategy_rejects_multiple_parameter_groups():
    optimizer = torch.optim.SGD(
        [
            {"params": [torch.nn.Parameter(torch.tensor(1.0))]},
            {"params": [torch.nn.Parameter(torch.tensor(2.0))]},
        ],
        lr=0.1,
    )

    with pytest.raises(ValueError, match="exactly one parameter group"):
        apply_optimizer_strategy([optimizer], {"lr": 0.2})
