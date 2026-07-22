from __future__ import annotations

import torch
from torch.utils.data import TensorDataset

from clan_based_tuning import ReplicatedDistributedSampler


def test_replicated_sampler_returns_the_full_dataset_on_every_member():
    dataset = TensorDataset(torch.arange(5))
    sampler = ReplicatedDistributedSampler(dataset)

    assert list(iter(sampler)) == [0, 1, 2, 3, 4]
    assert sampler.num_replicas == 1
    assert sampler.rank == 0
