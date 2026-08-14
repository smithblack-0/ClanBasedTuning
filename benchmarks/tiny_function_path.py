"""Measure the complete tiny Clan function path without a model or dataset download."""

import argparse
import json
import tempfile
import time
from pathlib import Path

import ray
from ray import tune

from tests.support.tiny_mlp import (
    build_tiny_scheduler,
    tiny_param_space,
    tiny_tune_config,
    train_tiny_mlp_member,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generations", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    """Run the tiny CPU Clan and print a compact JSON measurement record."""

    args = _parse_args()
    if args.generations < 1:
        raise ValueError("--generations must be positive")

    with tempfile.TemporaryDirectory() as storage_dir:
        ray.shutdown()
        ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
        started = time.perf_counter()
        try:
            results = tune.Tuner(
                tune.with_resources(train_tiny_mlp_member, {"cpu": 1}),
                param_space=tiny_param_space(accelerator="cpu"),
                tune_config=tiny_tune_config(build_tiny_scheduler()),
                run_config=tune.RunConfig(
                    name="tiny-function-path-benchmark",
                    storage_path=storage_dir,
                    stop={"training_iteration": args.generations},
                    verbose=0,
                ),
            ).fit()
        finally:
            wall_clock_s = time.perf_counter() - started
            ray.shutdown()

        if any(result.error is not None for result in results):
            raise RuntimeError("tiny function-path benchmark produced a failed member")

        checkpoint_files = list(Path(storage_dir).rglob("checkpoint.ckpt"))
        record = {
            "wall_clock_s": wall_clock_s,
            "population_size": len(results),
            "requested_generations": args.generations,
            "training_iterations": [
                int(result.metrics["training_iteration"]) for result in results
            ],
            "member_time_total_s": [float(result.metrics["time_total_s"]) for result in results],
            "checkpoint_count": len(checkpoint_files),
            "checkpoint_bytes": sum(path.stat().st_size for path in checkpoint_files),
            "final_val_loss": [float(result.metrics["val_loss"]) for result in results],
        }
        print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
