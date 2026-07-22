"""Explicit replicated evaluation sampling for comparable clan fitness."""

from __future__ import annotations

from torch.utils.data import Dataset
from torch.utils.data.distributed import DistributedSampler


def replicated_sampler(
    dataset: Dataset,
    *,
    shuffle: bool = False,
    seed: int = 0,
    drop_last: bool = False,
) -> DistributedSampler:
    """Return PyTorch's sampler configured to expose the full dataset per member."""

    return DistributedSampler(
        dataset,
        num_replicas=1,
        rank=0,
        shuffle=shuffle,
        seed=seed,
        drop_last=drop_last,
    )
