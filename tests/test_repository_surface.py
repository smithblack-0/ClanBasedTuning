"""Repository-level guard for the accepted Milestone 1 and 2 active surface."""

from pathlib import Path


def test_active_package_contains_only_accepted_controller_and_ray_transition_code():
    """Historical framework code must remain outside the active implementation."""

    repository_root = Path(__file__).resolve().parents[1]
    package_root = repository_root / "src" / "clan_based_tuning"
    source_files = {
        path.relative_to(repository_root).as_posix() for path in package_root.rglob("*.py")
    }

    assert source_files == {
        "src/clan_based_tuning/__init__.py",
        "src/clan_based_tuning/controller.py",
        "src/clan_based_tuning/controller_types.py",
        "src/clan_based_tuning/lightning_ddp.py",
        "src/clan_based_tuning/lightning_transition.py",
        "src/clan_based_tuning/member_state.py",
        "src/clan_based_tuning/ray_exchange.py",
        "src/clan_based_tuning/ray_rendezvous.py",
        "src/clan_based_tuning/ray_transition.py",
        "src/clan_based_tuning/tune_trainable.py",
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
        "tests/framework_contracts/test_ray_transition.py",
        "tests/framework_contracts/test_ray_exchange.py",
        "tests/framework_contracts/test_ray_rendezvous.py",
        "tests/framework_contracts/test_tune_trainable.py",
        "tests/framework_contracts/test_lightning_transition.py",
        "tests/framework_contracts/test_lightning_ddp.py",
        "tests/framework_contracts/test_manual_clan_tuning.py",
        "tests/test_package.py",
        "tests/test_repository_surface.py",
        "tests/unit/test_controller.py",
        "tests/unit/test_controller_types.py",
    }


def test_active_training_examples_use_only_the_rebuilt_manual_composition():
    """Historical examples must not return beside the accepted manual path."""

    repository_root = Path(__file__).resolve().parents[1]
    examples_root = repository_root / "examples"
    example_files = {
        path.relative_to(repository_root).as_posix() for path in examples_root.rglob("*.py")
    }

    assert example_files == {"examples/manual_clan_tuning.py"}
