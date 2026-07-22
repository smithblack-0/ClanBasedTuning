from __future__ import annotations

import torch
from torch.utils.data import TensorDataset
from torch.utils.data.distributed import DistributedSampler

from clan_based_tuning import replicated_sampler


def test_replicated_sampler_configures_pytorchs_builtin_sampler():
    dataset = TensorDataset(torch.arange(5))
    sampler = replicated_sampler(dataset)

    assert type(sampler) is DistributedSampler
    assert list(iter(sampler)) == [0, 1, 2, 3, 4]
    assert sampler.num_replicas == 1
    assert sampler.rank == 0
