"""Winner-local Lightning checkpoint serialization.

Lightning's public ``Trainer.save_checkpoint`` is deliberately collective and adds a
strategy barrier after serialization. Clan selection has already established that only
one process owns the state to preserve, so the losing processes must not enter that
barrier. This seam reuses Lightning's own checkpoint dump and strategy write while
omitting only the collective completion barrier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lightning import Trainer


def save_local_checkpoint(
    trainer: Trainer,
    filepath: str | Path,
    *,
    weights_only: bool | None = None,
    storage_options: Any | None = None,
) -> None:
    """Serialize one selected process's complete Lightning state without a barrier.

    This is a version-sensitive Milestone 3 integration seam. Lightning's checkpoint
    connector still owns checkpoint contents, including model, optimizer, loop, and
    callback state. The strategy and its configured ``CheckpointIO`` still own the
    write. Only ``Trainer.save_checkpoint``'s final distributed barrier is skipped.
    """

    if trainer.model is None:
        raise AttributeError(
            "Saving a checkpoint is only possible after a model is attached to Trainer"
        )
    checkpoint = trainer._checkpoint_connector.dump_checkpoint(weights_only)
    trainer.strategy.save_checkpoint(
        checkpoint,
        filepath,
        storage_options=storage_options,
    )
