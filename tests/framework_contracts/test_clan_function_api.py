"""End-to-end contract for the public Ray function + Lightning Clan path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def _train_member(genome):
    import tempfile
    from uuid import uuid4

    import lightning.pytorch as lightning
    import torch
    from lightning.pytorch.plugins.io import TorchCheckpointIO
    from ray import tune
    from torch.utils.data import DataLoader, TensorDataset

    from clan_based_tuning import ClanDDPStrategy, ClanTuneReportCallback

    torch.set_num_threads(1)

    class AuditCheckpointIO(TorchCheckpointIO):
        """Record every physical Lightning checkpoint write across the Clan."""

        def save_checkpoint(self, checkpoint, path, storage_options=None):
            super().save_checkpoint(checkpoint, path, storage_options=storage_options)
            audit_dir = Path(genome["checkpoint_audit_dir"])
            audit_dir.mkdir(parents=True, exist_ok=True)
            Path(audit_dir, uuid4().hex).touch()

    class ScalarModel(lightning.LightningModule):
        def __init__(self, current_genome):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(1.0))
            self.optimizer = torch.optim.SGD(
                self.parameters(),
                lr=current_genome["lr"],
                momentum=0.9,
            )

        def training_step(self, batch, batch_index):
            del batch, batch_index
            return self.weight

        def validation_step(self, batch, batch_index):
            del batch, batch_index
            self.log("val_loss", self.weight.square())
            self.log("lr_seen", self.optimizer.param_groups[0]["lr"])

        def configure_optimizers(self):
            return self.optimizer

    model = ScalarModel(genome)
    checkpoint = tune.get_checkpoint()
    checkpoint_context = tempfile.TemporaryDirectory()
    checkpoint_path = None

    if checkpoint is not None:
        checkpoint_dir = checkpoint.to_directory(checkpoint_context.name)
        checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

        # This is deliberately userspace PBT-style application. CBT neither owns nor
        # calls it: restore the inherited optimizer history, then inject the new genome.
        model.optimizer.load_state_dict(state["optimizer_states"][0])
        for param_group in model.optimizer.param_groups:
            param_group["lr"] = genome["lr"]
        state["optimizer_states"][0] = model.optimizer.state_dict()
        torch.save(state, checkpoint_path)

    data = DataLoader(TensorDataset(torch.tensor([0.0])), batch_size=1)
    trainer = lightning.Trainer(
        accelerator="cpu",
        devices=1,
        strategy=ClanDDPStrategy(
            checkpoint_io=AuditCheckpointIO(),
        ),
        callbacks=[ClanTuneReportCallback(extra_metrics=["lr_seen"])],
        max_epochs=100,
        num_sanity_val_steps=0,
        logger=False,
        enable_checkpointing=False,
        enable_model_summary=False,
        enable_progress_bar=False,
    )
    trainer.fit(
        model,
        train_dataloaders=data,
        val_dataloaders=data,
        ckpt_path=str(checkpoint_path) if checkpoint_path is not None else None,
    )


def test_function_trainable_repeats_clan_transition_with_one_checkpoint_per_round(tmp_path):
    import ray
    from ray import tune

    from clan_based_tuning import ClanScheduler, MutationSpec

    checkpoint_audit_dir = tmp_path / "checkpoint-writes"

    ray.shutdown()
    ray.init(num_cpus=2, include_dashboard=False, log_to_driver=False)
    try:
        scheduler = ClanScheduler(
            population_size=2,
            metric="val_loss",
            mode="min",
            mutations={
                "lr": MutationSpec(
                    standard_deviation=0.15,
                    geometry="log",
                    minimum=0.02,
                    maximum=0.5,
                )
            },
            seed=7,
            join_timeout_s=60.0,
        )
        tuner = tune.Tuner(
            tune.with_resources(scheduler.wrap(_train_member), {"cpu": 1}),
            param_space={
                "lr": tune.grid_search([0.1, 0.2]),
                "checkpoint_audit_dir": str(checkpoint_audit_dir),
            },
            tune_config=tune.TuneConfig(
                scheduler=scheduler,
                max_concurrent_trials=2,
            ),
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
        genome = json.loads(result.metrics["clan/genome_json"])
        assert result.metrics["lr_seen"] == pytest.approx(genome["lr"])

    # Each of two rounds produces exactly one actual Lightning persistence call, even
    # though both ranks construct checkpoint state and enter the save barrier.
    assert len(list(checkpoint_audit_dir.iterdir())) == 2

    # Ray's persisted continuation also remains one source artifact per round rather than
    # one checkpoint file per member.
    checkpoint_files = list(Path(tmp_path).rglob("checkpoint.ckpt"))
    assert 1 <= len(checkpoint_files) <= 2
