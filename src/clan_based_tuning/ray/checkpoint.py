"""Small adapter from Ray Tune checkpoints to Lightning checkpoint paths."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def tune_checkpoint_path(filename: str = "checkpoint") -> Iterator[str | None]:
    """Yield the current Tune checkpoint file for ``Trainer.fit(ckpt_path=...)``.

    Ray owns checkpoint transport and restoration, but Lightning needs a file
    path that remains valid for the full fit call. This context manager keeps
    Ray's materialized checkpoint directory alive for exactly that lifecycle.
    """

    if not filename:
        raise ValueError("filename must be non-empty")
    try:
        from ray import tune
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            'Ray Tune support requires: pip install "clan-based-tuning[ray]"'
        ) from error

    checkpoint = tune.get_checkpoint()
    if checkpoint is None:
        yield None
        return

    with checkpoint.as_directory() as directory:
        path = Path(directory, filename)
        if not path.is_file():
            raise FileNotFoundError(
                f"Tune checkpoint does not contain expected Lightning file {filename!r}"
            )
        yield str(path)
