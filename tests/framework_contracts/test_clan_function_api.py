"""End-to-end contracts for the public Ray function + Lightning Clan lifecycle.

These tests use real Ray, Lightning, PyTorch, Tune checkpoints, and process-group collectives.
The first contract proves repeated single-parent transitions. The second intentionally fails
a restored member only after Lightning has restored training state, then restarts Ray and
requires ordinary ``Tuner.restore`` to reconstruct the Clan and continue.
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
    """Run one real Tune member while exposing state needed by lifecycle assertions."""

    torch.set_num_threads(1)

    class ScalarModel(lightning.LightningModule):
        """Minimal model whose optimizer state makes continuation directly observable."""

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
            """Apply the current genome after Lightning has restored inherited state."""

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
            """Expose the DDP-partitioned sample and produce a simple common gradient."""

            del batch_index
            self.training_sample_value = float(batch[0].item())
            return self.weight

        def on_before_optimizer_step(self, optimizer: torch.optim.Optimizer) -> None:
            """Record whether selected-parent optimizer momentum survived restoration."""

            state = optimizer.state[self.weight]
            momentum = state.get("momentum_buffer")
            self.momentum_before_step = 0.0 if momentum is None else float(momentum.detach().item())

        def on_validation_epoch_start(self) -> None:
            """Reset complete-validation accounting for this member."""

            self.validation_sample_sum = 0.0
            self.validation_sample_count = 0

        def validation_step(self, batch: list[torch.Tensor], batch_index: int) -> None:
            """Record complete held-out coverage and member-local candidate metrics."""

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
            """Publish coverage evidence after Lightning-managed validation completes."""

            if not self.trainer.sanity_checking:
                self.log("validation_sample_sum", self.validation_sample_sum)
                self.log("validation_sample_count", float(self.validation_sample_count))

        def configure_optimizers(self) -> torch.optim.Optimizer:
            """Return the optimizer whose inherited state is part of the Clan continuation."""

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
    """Build the deterministic two-member scheduler shared by framework contracts."""

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
    """Use the ordinary Tune metric/mode/scheduler configuration surface."""

    return tune.TuneConfig(
        scheduler=scheduler,
        metric="val_loss",
        mode="min",
    )


def test_function_trainable_repeats_one_parent_transition(tmp_path: Path) -> None:
    """Two members inherit complete state and both receive seeded sibling mutations."""

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
    """Fresh Ray restores errored members after an intentional failure following state load."""

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
