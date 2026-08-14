"""Distribution-artifact contracts for the installable package."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def test_wheel_is_clean_and_importable_without_repository_or_optional_dependencies(tmp_path):
    repository_root = Path(__file__).resolve().parents[1]
    dist_dir = tmp_path / "dist"
    install_dir = tmp_path / "installed"

    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(dist_dir)],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )

    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    assert len(wheels) == 1
    assert len(sdists) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        packaged_paths = set(wheel.namelist())

    assert "clan_based_tuning/__init__.py" in packaged_paths
    assert not any(path.startswith("tests/") for path in packaged_paths)
    assert not any(path.startswith("examples/") for path in packaged_paths)
    assert not any(path.startswith("docs/") for path in packaged_paths)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(install_dir),
            str(wheels[0]),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(install_dir)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json, clan_based_tuning; print(json.dumps(clan_based_tuning.__all__))",
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == [
        "ClanDDPStrategy",
        "ClanScheduler",
        "ClanTuneReportCallback",
    ]
