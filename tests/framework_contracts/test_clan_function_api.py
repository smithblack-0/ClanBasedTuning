"""End-to-end contracts for the public Ray function + Lightning Clan lifecycle.

These tests intentionally cross real framework boundaries rather than isolating CBT. The first
proves that two ordinary Tune functions form one Lightning DDP world, diverge only after the
shared gradient, select one parent, and inherit its complete Lightning/optimizer state. The
second fails only after a restored invocation reaches userspace, restarts Ray entirely, and
requires ordinary ``Tuner.restore`` to reconstruct CBT runtime authority without a special
restore API.
"""

import contextlib
import tempfile
from pathlib import Path
from typing import Any

import lightning.pytorch as lightning
import pytest
import ray
import torch
from ray import tune
from ray.tune.error import TuneError
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def _train_member(genome: dict[str, Any]) -> None:
    """Expose just enough real training state to prove the complete continuation contract.

    The scalar model is intentionally transparent rather than realistic: weight, momentum,
    global step, training partition, validation coverage, and applied learning rate all become
    independently observable. That lets one test distinguish "checkpoint copied" from the
    stronger requirement that selected model state, optimizer history, Lightning progress,
    replicated validation, and userspace child-genome application all survive the transition.
    """

    torch.set_num_threads(1)

    class ScalarModel(lightning.LightningModule):
        """Make every state component that should cross a Clan boundary directly observable."""

        def __init__(self, current_genome: dict[str, Any]) -> None:
            super().__init__()
            self.genome = current_genome
            self.weight = torch.nn.Parameter(torch.tensor(1.0))
            self.optimizer = torch.optim.SGD(
                self.parameters(),
                lr=float(current_genome["lr"]),
                momentum=0.9,
            )
            self.round_start_weight: float | None = None
            self.round_start_global_step: float | None = None
            self.momentum_before_step: float | None = None
            self.training_sample_value: float | None = None
            self.validation_sample_sum = 0.0
            self.validation_sample_count = 0

        def on_train_start(self) -> None:
            """Prove restore precedes userspace child-genome application, then optionally fail.

            Start-of-round weight/global step are sampled before new training mutates them. The
            marker-controlled failure is deliberately placed here: observing its external file
            proves the interrupted restore test reached this hook with nonzero restored
            Lightning progress rather than failing earlier in Tune or checkpoint loading.
            """

            for param_group in self.optimizer.param_groups:
                param_group["lr"] = float(self.genome["lr"])

            self.round_start_weight = float(self.weight.detach().item())
            self.round_start_global_step = float(self.trainer.global_step)

            if "fail_on_restore_marker" in self.genome:
                failure_marker = Path(str(self.genome["fail_on_restore_marker"]))
                observed_marker = Path(str(self.genome["failure_observed_marker"]))
                if self.trainer.global_step > 0 and failure_marker.exists():
                    observed_marker.write_text("failure reached after restore")
                    raise RuntimeError("intentional interrupted-run qualification failure")

        def training_step(self, batch: list[torch.Tensor], batch_index: int) -> torch.Tensor:
            """Make DDP data partitioning visible while keeping the common gradient trivial."""

            del batch_index
            self.training_sample_value = float(batch[0].item())
            return self.weight

        def on_before_optimizer_step(self, optimizer: torch.optim.Optimizer) -> None:
            """Observe inherited momentum after DDP reduction, before the next update changes it."""

            state = optimizer.state[self.weight]
            momentum = state.get("momentum_buffer")
            self.momentum_before_step = 0.0 if momentum is None else float(momentum.detach().item())

        def on_validation_epoch_start(self) -> None:
            """Start fresh coverage accounting for each member's independently complete validation."""

            self.validation_sample_sum = 0.0
            self.validation_sample_count = 0

        def validation_step(self, batch: list[torch.Tensor], batch_index: int) -> None:
            """Accumulate full-workload evidence while keeping fitness member-local."""

            del batch_index
            values = batch[0]
            self.validation_sample_sum += float(values.sum().item())
            self.validation_sample_count += int(values.numel())
            if not self.trainer.sanity_checking:
                self.log("val_loss", self.weight.square())
                self.log("lr_seen", self.optimizer.param_groups[0]["lr"])
                self.log("round_start_weight", self.round_start_weight)
                self.log("round_start_global_step", self.round_start_global_step)
                self.log("momentum_before_step", self.momentum_before_step)
                self.log("training_sample_value", self.training_sample_value)

        def on_validation_epoch_end(self) -> None:
            """Publish coverage after Lightning traverses the complete validation loader."""

            if not self.trainer.sanity_checking:
                self.log("validation_sample_sum", self.validation_sample_sum)
                self.log("validation_sample_count", float(self.validation_sample_count))

        def configure_optimizers(self) -> torch.optim.Optimizer:
            """Keep optimizer ownership in userspace so inherited momentum tests the public path."""

            return self.optimizer

    model = ScalarModel(genome)
    checkpoint = tune.get_checkpoint()

    with tempfile.TemporaryDirectory() as local_checkpoint_dir:
        checkpoint_path = None
        if checkpoint is not None:
            checkpoint_dir = checkpoint.to_directory(local_checkpoint_dir)
            checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")

        train_data = DataLoader(
            TensorDataset(torch.tensor([0.0, 1.0, 2.0, 3.0])),
            batch_size=1,
            shuffle=False,
        )
        validation_data = DataLoader(
            TensorDataset(torch.tensor([0.0, 1.0, 2.0, 3.0])),
            batch_size=1,
            shuffle=False,
        )
        trainer = lightning.Trainer(
            accelerator="cpu",
            strategy=ClanDDPStrategy(),
            callbacks=[
                ClanTuneReportCallback(
                    extra_metrics=[
                        "lr_seen",
                        "round_start_weight",
                        "round_start_global_step",
                        "momentum_before_step",
                        "training_sample_value",
                        "validation_sample_sum",
                        "validation_sample_count",
                    ]
                )
            ],
            max_epochs=100,
            logger=False,
            enable_checkpointing=False,
            enable_model_summary=False,
            enable_progress_bar=False,
            limit_train_batches=1,
        )
        trainer.fit(
            model,
            train_dataloaders=train_data,
            val_dataloaders=validation_data,
            ckpt_path=str(checkpoint_path) if checkpoint_path is not None else None,
        )


def _scheduler(population_size: int = 2) -> ClanScheduler:
    """Hold mutation/seed semantics constant between transition and restore contracts.

    ``population_size`` is exposed only because malformed/capacity variants occasionally need
    the same scheduler policy with a different cohort shape; all mutation semantics remain one
    source of truth so restore tests cannot accidentally qualify a different algorithm.
    """

    return ClanScheduler(
        population_size=population_size,
        mutations={
            "lr": {
                "standard_deviation": 0.15,
                "geometry": "log",
                "minimum": 0.02,
                "maximum": 0.5,
            }
        },
        seed=7,
        join_timeout_s=60.0,
    )


def _tune_config(scheduler: ClanScheduler) -> tune.TuneConfig:
    """Keep driver selection metric/direction identical across all lifecycle contracts."""

    return tune.TuneConfig(
        scheduler=scheduler,
        metric="val_loss",
        mode="min",
    )


def test_function_trainable_repeats_one_parent_transition(tmp_path: Path) -> None:
    """One transition preserves full parent state while producing two seeded child policies."""

    ray.shutdown()
    ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
    try:
        tuner = tune.Tuner(
            tune.with_resources(_train_member, {"cpu": 1}),
            param_space={"lr": tune.grid_search([0.1, 0.2])},
            tune_config=_tune_config(_scheduler()),
            run_config=tune.RunConfig(
                name="function-api-clan-contract",
                storage_path=str(tmp_path),
                stop={"training_iteration": 2},
                verbose=0,
            ),
        )
        results = tuner.fit()
    finally:
        ray.shutdown()

    assert len(results) == 2
    assert all(result.error is None for result in results)

    for result in results:
        assert result.metrics["training_iteration"] >= 2
        assert result.metrics["lr_seen"] == pytest.approx(result.config["lr"])
        assert result.metrics["round_start_weight"] == pytest.approx(0.8)
        assert result.metrics["round_start_global_step"] == pytest.approx(1.0)
        assert result.metrics["momentum_before_step"] == pytest.approx(1.0)
        assert result.metrics["validation_sample_count"] == pytest.approx(4.0)
        assert result.metrics["validation_sample_sum"] == pytest.approx(6.0)

    training_samples = [result.metrics["training_sample_value"] for result in results]
    assert len(set(training_samples)) == 2
    assert all(sample in {0.0, 1.0, 2.0, 3.0} for sample in training_samples)

    final_lrs = sorted(result.config["lr"] for result in results)
    assert final_lrs == pytest.approx(sorted([0.1924690426284743, 0.2159468026720305]))

    checkpoint_files = list(Path(tmp_path).rglob("checkpoint.ckpt"))
    assert 1 <= len(checkpoint_files) <= 2


def test_tuner_restore_rebuilds_runtime_after_post_restore_failure(tmp_path: Path) -> None:
    """Fresh Ray must reconstruct CBT authority after failure proven to occur post-restore.

    The external marker establishes failure ordering before the first Ray runtime is destroyed.
    Removing only the trigger and using ordinary ``Tuner.restore(..., resume_errored=True)``
    then proves scheduler serialization contains enough durable authority to recreate named
    runtime actors and continue both members without user reconstruction code.
    """

    experiment_name = "function-api-restore-contract"
    experiment_path = tmp_path / experiment_name
    marker = tmp_path / "fail-on-restored-invocation"
    observed = tmp_path / "failure-observed-after-restore"
    marker.write_text("fail")

    ray.shutdown()
    ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
    try:
        tuner = tune.Tuner(
            tune.with_resources(_train_member, {"cpu": 1}),
            param_space={
                "lr": tune.grid_search([0.1, 0.2]),
                "fail_on_restore_marker": str(marker),
                "failure_observed_marker": str(observed),
            },
            tune_config=_tune_config(_scheduler()),
            run_config=tune.RunConfig(
                name=experiment_name,
                storage_path=str(tmp_path),
                stop={"training_iteration": 3},
                verbose=0,
            ),
        )
        with contextlib.suppress(TuneError):
            tuner.fit()
    finally:
        ray.shutdown()

    assert observed.exists(), "the injected failure must occur only after Lightning restoration"
    assert tune.Tuner.can_restore(str(experiment_path))
    marker.unlink()

    ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
    try:
        restored = tune.Tuner.restore(
            str(experiment_path),
            trainable=tune.with_resources(_train_member, {"cpu": 1}),
            resume_errored=True,
        )
        results = restored.fit()
    finally:
        ray.shutdown()

    assert len(results) == 2
    assert all(result.error is None for result in results)
    assert all(result.metrics["training_iteration"] >= 3 for result in results)
    assert all(
        result.metrics["lr_seen"] == pytest.approx(result.config["lr"]) for result in results
    )
    assert all(result.metrics["round_start_global_step"] >= 1 for result in results)
