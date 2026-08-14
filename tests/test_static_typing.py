"""Static-typing quality contract for the shipped package source.

The package advertises PEP 561 typing, so the repository's normal validation must prove that
all package function definitions remain annotated and pass the maintained mypy policy. The
framework boundaries are intentionally treated as external/dynamic; this contract checks CBT's
own source rather than attempting to type-check Ray, Lightning, or PyTorch internals.
"""

import subprocess
import sys
from pathlib import Path


def test_package_source_passes_mypy_policy() -> None:
    """The shipped package source satisfies the repository's configured static checker."""

    repository_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "mypy", "src/clan_based_tuning", "--show-error-codes"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
