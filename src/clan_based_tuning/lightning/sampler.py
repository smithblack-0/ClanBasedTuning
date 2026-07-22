"""Evaluation sampler that gives every clan member the same examples."""

from __future__ import annotations

from torch.utils.data import Dataset
from torch.utils.data.distributed import DistributedSampler


class ReplicatedDistributedSampler(DistributedSampler):
    """Present a full deterministic dataset to every clan member.

    Lightning preserves user-provided ``DistributedSampler`` instances instead
    of replacing them. Declaring one logical replica therefore keeps training
    dataloaders normally sharded while allowing a validation dataloader to be
    replicated for comparable member fitness.
    """

    def __init__(
        self,
        dataset: Dataset,
        *,
        shuffle: bool = False,
        seed: int = 0,
        drop_last: bool = False,
    ) -> None:
        super().__init__(
            dataset,
            num_replicas=1,
            rank=0,
            shuffle=shuffle,
            seed=seed,
            drop_last=drop_last,
        )
