"""Distribution-artifact contracts for the installable ClanBasedTuning package.

The test builds wheel/sdist artifacts, verifies runtime dependency and typing metadata,
installs the wheel non-editably into an isolated target directory, and imports the actual
public integration objects from that artifact rather than from the repository source tree.
"""

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def test_wheel_declares_runtime_dependencies_and_imports_public_surface(tmp_path: Path) -> None:
    """The built wheel is clean, typed, self-describing, and exposes the public surface."""

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
        metadata_path = next(
            path for path in packaged_paths if path.endswith(".dist-info/METADATA")
        )
        metadata = wheel.read(metadata_path).decode("utf-8")

    assert "clan_based_tuning/__init__.py" in packaged_paths
    assert "clan_based_tuning/py.typed" in packaged_paths
    assert not any(path.startswith("tests/") for path in packaged_paths)
    assert not any(path.startswith("examples/") for path in packaged_paths)
    assert not any(path.startswith("docs/") for path in packaged_paths)
    assert "Classifier: Typing :: Typed" in metadata
    assert "Requires-Dist: lightning<3,>=2.6" in metadata
    assert "Requires-Dist: ray[tune]<3,>=2.56" in metadata
    assert "Requires-Dist: torch<3,>=2.10" in metadata

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
            (
                "import json, clan_based_tuning as cbt; "
                "print(json.dumps([cbt.__all__, cbt.ClanScheduler.__name__, "
                "cbt.ClanDDPStrategy.__name__, cbt.ClanTuneReportCallback.__name__]))"
            ),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == [
        ["ClanDDPStrategy", "ClanScheduler", "ClanTuneReportCallback"],
        "ClanScheduler",
        "ClanDDPStrategy",
        "ClanTuneReportCallback",
    ]
