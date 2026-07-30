"""Repository-level guard for the accepted active implementation surface."""

from pathlib import Path


def test_active_package_contains_only_the_accepted_implementation():
    """Only accepted controller and collective-failure code is importable."""

    repository_root = Path(__file__).resolve().parents[1]
    package_root = repository_root / "src" / "clan_based_tuning"
    source_files = {
        path.relative_to(repository_root).as_posix() for path in package_root.rglob("*.py")
    }

    assert source_files == {
        "src/clan_based_tuning/__init__.py",
        "src/clan_based_tuning/controller.py",
        "src/clan_based_tuning/controller_types.py",
        "src/clan_based_tuning/ray_schedulers.py",
    }


def test_test_suite_contains_only_current_surface_contracts():
    """Removed integration tests must not continue asserting obsolete architecture."""

    repository_root = Path(__file__).resolve().parents[1]
    tests_root = repository_root / "tests"
    test_files = {
        path.relative_to(repository_root).as_posix()
        for path in tests_root.rglob("*.py")
        if path.name != "__init__.py"
    }

    assert test_files == {
        "tests/framework_contracts/test_ray_collective_failure_scheduler.py",
        "tests/framework_contracts/test_removed_integration_surface.py",
        "tests/test_package.py",
        "tests/test_repository_surface.py",
        "tests/unit/test_controller.py",
        "tests/unit/test_controller_types.py",
        "tests/unit/test_ray_schedulers.py",
    }


def test_no_active_training_example_survives_the_reset():
    """Milestone 3 examples must be rebuilt from accepted integration primitives."""

    repository_root = Path(__file__).resolve().parents[1]
    examples_root = repository_root / "examples"
    example_files = list(examples_root.rglob("*.py")) if examples_root.exists() else []

    assert example_files == []
