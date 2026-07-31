"""Repository-level guard for the accepted active implementation surface."""

from pathlib import Path


def test_active_package_contains_only_the_thin_worker_core():
    """Historical integration and superseded round code stay outside the source tree."""

    repository_root = Path(__file__).resolve().parents[1]
    package_root = repository_root / "src" / "clan_based_tuning"
    source_files = {
        path.relative_to(repository_root).as_posix() for path in package_root.rglob("*.py")
    }

    assert source_files == {
        "src/clan_based_tuning/__init__.py",
        "src/clan_based_tuning/controller.py",
        "src/clan_based_tuning/controller_types.py",
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
        "tests/framework_contracts/test_removed_integration_surface.py",
        "tests/test_package.py",
        "tests/test_repository_surface.py",
        "tests/unit/test_controller.py",
        "tests/unit/test_controller_types.py",
    }


def test_no_active_training_example_precedes_the_new_integration():
    """Examples must be rebuilt only after the accepted Tune and Lightning seams."""

    repository_root = Path(__file__).resolve().parents[1]
    examples_root = repository_root / "examples"
    example_files = list(examples_root.rglob("*.py")) if examples_root.exists() else []

    assert example_files == []
