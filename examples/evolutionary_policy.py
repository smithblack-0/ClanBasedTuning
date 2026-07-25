"""Inspect one framework-independent Clan population decision."""

from __future__ import annotations

import json

from clan_based_tuning import ClanPopulationPolicy, MemberResult


def main() -> None:
    """Run one population decision and print its inspectable result."""

    population = {
        "trial-0": MemberResult(
            fitness=0.42,
            optimizer_config={"lr": 3e-4, "weight_decay": 0.01, "batch_size": 128},
        ),
        "trial-1": MemberResult(
            fitness=0.38,
            optimizer_config={"lr": 2e-4, "weight_decay": 0.02, "batch_size": 128},
        ),
        "trial-2": MemberResult(
            fitness=0.47,
            optimizer_config={"lr": 4e-4, "weight_decay": 0.005, "batch_size": 128},
        ),
        "trial-3": MemberResult(
            fitness=0.44,
            optimizer_config={"lr": 3.5e-4, "weight_decay": 0.015, "batch_size": 128},
        ),
    }

    policy = ClanPopulationPolicy(
        mode="min",
        field_factors={
            "lr": (0.8, 1.2),
            "weight_decay": (0.5, 2.0),
        },
    )
    decision = policy.decide(population, seed=17)

    print("Selected parent:")
    print(f"  {decision.parent_id} with fitness {decision.parent_fitness}")
    print("\nNext-generation optimizer configurations:")
    print(json.dumps(decision.optimizer_configs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
