"""Static-typing quality contract for the shipped package source.

The package advertises PEP 561 typing, so repository validation must exercise the same checker
policy contributors are expected to maintain. Framework libraries remain dynamic external
boundaries; this contract asks whether CBT's own annotated source is internally consistent,
not whether Ray/Lightning/PyTorch type stubs are complete.
"""

import subprocess
import sys
from pathlib import Path


def test_package_source_passes_mypy_policy() -> None:
    """Run mypy from the repository root so project configuration is part of the contract.

    A subprocess is intentional here: importing mypy APIs would bypass or partially duplicate
    the command/config path contributors and CI actually use, weakening the value of the gate.
    """

    repository_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "mypy", "src/clan_based_tuning", "--show-error-codes"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
