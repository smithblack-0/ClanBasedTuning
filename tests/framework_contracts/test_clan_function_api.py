"""End-to-end contract for the public Ray function + Lightning Clan path."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


def _train_member(genome):
    import tempfile

    import lightning.pytorch as lightning
    import torch
    from ray import tune
    from torch.utils.data import DataLoader, TensorDataset

    from clan_based_tuning import ClanDDPStrategy, ClanTuneReportCallback

    torch.set_num_threads(1)

    class ScalarModel(lightning.LightningModule):
        def __init__(self, current_genome):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(1.0))
            self.optimizer = torch.optim.SGD(
                self.parameters(),
                lr=current_genome["lr"],
                momentum=0.9,
            )
            self.round_start_weight = None
            self.round_start_global_step = None
            self.momentum_before_step = None
            self.training_sample_value = None
            self.validation_sample_sum = 0.0
            self.validation_sample_count = 0

        def training_step(self, batch, batch_index):
            del batch_index
            self.training_sample_value = float(batch[0].item())
            return self.weight

        def on_train_start(self):
            self.round_start_weight = float(self.weight.detach().item())
            self.round_start_global_step = float(self.trainer.global_step)

        def on_before_optimizer_step(self, optimizer):
            state = optimizer.state[self.weight]
            momentum = state.get("momentum_buffer")
            self.momentum_before_step = 0.0 if momentum is None else float(momentum.detach().item())

        def on_validation_epoch_start(self):
            self.validation_sample_sum = 0.0
            self.validation_sample_count = 0

        def validation_step(self, batch, batch_index):
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

        def on_validation_epoch_end(self):
            if not self.trainer.sanity_checking:
                self.log("validation_sample_sum", self.validation_sample_sum)
                self.log("validation_sample_count", float(self.validation_sample_count))

        def configure_optimizers(self):
            return self.optimizer

    model = ScalarModel(genome)
    checkpoint = tune.get_checkpoint()
    local_checkpoint = tempfile.TemporaryDirectory()
    checkpoint_path = None

    if checkpoint is not None:
        checkpoint_dir = checkpoint.to_directory(local_checkpoint.name)
        checkpoint_path = Path(checkpoint_dir, "checkpoint.ckpt")
        state = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=False,
        )

        # USERSPACE. CBT does not inspect, call, or know the meaning of this operation.
        # Restore inherited optimizer history, apply this member's current genome, and
        # place the user-modified optimizer state back into the local Lightning copy.
        model.optimizer.load_state_dict(state["optimizer_states"][0])
        for param_group in model.optimizer.param_groups:
            param_group["lr"] = genome["lr"]
        state["optimizer_states"][0] = model.optimizer.state_dict()
        torch.save(state, checkpoint_path)

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
        devices=1,
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


def test_function_trainable_repeats_clan_transition_with_one_checkpoint_per_round(tmp_path):
    import ray
    from ray import tune

    from clan_based_tuning import ClanScheduler, MutationSpec

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
            param_space={"lr": tune.grid_search([0.1, 0.2])},
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
        assert result.metrics["lr_seen"] == pytest.approx(result.config["lr"])
        assert result.metrics["round_start_weight"] == pytest.approx(0.8)
        assert result.metrics["round_start_global_step"] == pytest.approx(1.0)
        assert result.metrics["momentum_before_step"] == pytest.approx(1.0)
        assert result.metrics["validation_sample_count"] == pytest.approx(4.0)
        assert result.metrics["validation_sample_sum"] == pytest.approx(6.0)

    # Training remains normally partitioned across ranks. With shuffle disabled and one
    # training batch, rank 0 receives sample 0 and rank 1 receives sample 1.
    training_samples = sorted(result.metrics["training_sample_value"] for result in results)
    assert training_samples == pytest.approx([0.0, 1.0])

    # The first winner used lr=0.2. Every second-round member receives an independent
    # deterministic mutation of that same selected parent genome, including the winner.
    final_lrs = sorted(result.config["lr"] for result in results)
    assert final_lrs == pytest.approx(sorted([0.1924690426284743, 0.2159468026720305]))

    # The selected first-round model state and Lightning progress are the common
    # second-round continuation.
    assert len({round(result.metrics["round_start_weight"], 7) for result in results}) == 1
    assert len({result.metrics["round_start_global_step"] for result in results}) == 1

    # Lightning's automatically injected validation sampler is replicated rather than
    # rank-sharded, including when the loader is first prepared for sanity validation.
    assert len({result.metrics["validation_sample_sum"] for result in results}) == 1
    assert len({result.metrics["validation_sample_count"] for result in results}) == 1

    # All ranks may materialize checkpoint state at the Lightning barrier, but only one
    # persistent CBT continuation exists per completed round.
    checkpoint_files = list(Path(tmp_path).rglob("checkpoint.ckpt"))
    assert 1 <= len(checkpoint_files) <= 2
