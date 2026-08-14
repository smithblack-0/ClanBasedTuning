"""Repository-level guard for the accepted active implementation surface."""

from pathlib import Path


def test_active_package_contains_only_current_accepted_components():
    """Superseded round and standalone collective code stay outside the source tree."""

    repository_root = Path(__file__).resolve().parents[1]
    package_root = repository_root / "src" / "clan_based_tuning"
    source_files = {
        path.relative_to(repository_root).as_posix() for path in package_root.rglob("*.py")
    }

    assert source_files == {
        "src/clan_based_tuning/__init__.py",
        "src/clan_based_tuning/controller.py",
        "src/clan_based_tuning/evolution.py",
        "src/clan_based_tuning/lightning_callback.py",
        "src/clan_based_tuning/lightning_environment.py",
        "src/clan_based_tuning/lightning_strategy.py",
        "src/clan_based_tuning/protocol.py",
        "src/clan_based_tuning/runtime.py",
        "src/clan_based_tuning/scheduler.py",
        "src/clan_based_tuning/scheduler_types.py",
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
        "tests/framework_contracts/test_clan_function_api.py",
        "tests/framework_contracts/test_removed_integration_surface.py",
        "tests/framework_contracts/test_tune_member_lightning_environment.py",
        "tests/test_package.py",
        "tests/test_repository_surface.py",
        "tests/unit/test_controller.py",
        "tests/unit/test_evolution.py",
    }


def test_production_package_does_not_own_genome_application():
    """Genome interpretation stays entirely in the user's Tune function."""

    repository_root = Path(__file__).resolve().parents[1]
    package_root = repository_root / "src" / "clan_based_tuning"
    source = "\n".join(path.read_text() for path in package_root.rglob("*.py"))

    assert "apply_genome" not in source
    assert "optimizer.param_groups" not in source
    assert "load_optimizer_state_dict" not in source


def test_no_active_training_example_precedes_the_new_integration():
    """Examples remain separate until the function API contract is qualified."""

    repository_root = Path(__file__).resolve().parents[1]
    examples_root = repository_root / "examples"
    example_files = list(examples_root.rglob("*.py")) if examples_root.exists() else []

    assert example_files == []
