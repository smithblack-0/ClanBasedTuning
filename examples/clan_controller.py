"""Inspect initialization and one framework-independent Clan transition."""

from __future__ import annotations

import json

from clan_based_tuning import ClanController


def main() -> None:
    """Run one reproducible population transition and print the policy result."""

    controller = ClanController(
        population_size=4,
        parameters={
            "lr": {
                "default": 3e-4,
                "std": 0.25,
                "sampling": "log",
                "lower": 1e-5,
                "upper": 1e-2,
            },
            "weight_decay": {
                "default": 0.01,
                "std": 0.005,
                "sampling": "linear",
                "lower": 0.0,
                "upper": 0.1,
            },
        },
        mode="min",
    )

    initial_configs = controller.initialize(
        ["trial-0", "trial-1", "trial-2", "trial-3"],
        seed=11,
    )
    population = {
        "trial-0": {"fitness": 0.42, "config": initial_configs["trial-0"]},
        "trial-1": {"fitness": 0.38, "config": initial_configs["trial-1"]},
        "trial-2": {"fitness": 0.47, "config": initial_configs["trial-2"]},
        "trial-3": {"fitness": 0.44, "config": initial_configs["trial-3"]},
    }

    parent_id, next_configs = controller.advance(population, seed=17)

    print("Initial optimizer configurations:")
    print(json.dumps(initial_configs, indent=2, sort_keys=True))
    print(f"\nSelected parent: {parent_id}")
    print("\nNext-generation optimizer configurations:")
    print(json.dumps(next_configs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
