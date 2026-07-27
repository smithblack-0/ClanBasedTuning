"""Run the Milestone 3 two-member Clan Tuning mechanics composition.

Each Ray Tune trial is one process-local member. Lightning executes one
train/validation window per Tune step, while native cross-trial PyTorch DDP
averages the distinct member gradients. The reported columns make the common
gradient, optimizer-driven model divergence, comparable fitness, selected
winner, and next member-local optimizer configuration inspectable.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import ray
import torch
from lightning import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback
from ray import tune
from ray.tune import RunConfig, TuneConfig, Tuner
from torch import Tensor
from torch.utils.data import DataLoader, TensorDataset

from clan_based_tuning import ClanController, MutationSpec
from clan_based_tuning.lightning_ddp import ClanDDPStrategy
from clan_based_tuning.member_state import NEXT_MEMBER_STATE, OPTIMIZER_CONFIG, WINNER_ID
from clan_based_tuning.ray_exchange import RayControllerCallbacks
from clan_based_tuning.ray_rendezvous import RayClanRuntimeExchange
from clan_based_tuning.ray_transition import MEMBER_ID, ROUND_INDEX, ClanTrialScheduler
from clan_based_tuning.tune_trainable import RUNTIME_EXCHANGE, ClanLightningTrainable

POPULATION_SIZE = 2
DEFAULT_ROUNDS = 3
FITNESS = "validation_loss"
OBSERVABILITY_METRICS = (
    FITNESS,
    "model_weight",
    "shared_gradient",
    "optimizer_lr",
    "training_target",
)


class ScalarRegression(LightningModule):
    """Expose shared-gradient mechanics with one scalar parameter."""

    def __init__(self, *, member_id: int):
        super().__init__()
        self.member_id = member_id
        self.weight = torch.nn.Parameter(torch.zeros(()))
        self._shared_gradient = torch.tensor(float("nan"))

    def training_step(self, batch: tuple[Tensor, Tensor], batch_index: int) -> Tensor:
        del batch_index
        features, targets = batch
        predictions = features.flatten() * self.weight
        return torch.nn.functional.mse_loss(predictions, targets.flatten())

    def on_before_optimizer_step(self, optimizer) -> None:
        del optimizer
        if self.weight.grad is None:
            raise RuntimeError("the scalar model reached its optimizer without a gradient")
        self._shared_gradient = self.weight.grad.detach().clone()

    def validation_step(self, batch: tuple[Tensor, Tensor], batch_index: int) -> None:
        del batch_index
        features, targets = batch
        predictions = features.flatten() * self.weight
        validation_loss = torch.nn.functional.mse_loss(predictions, targets.flatten())
        optimizer_lr = self.optimizers().param_groups[0]["lr"]
        training_target = float(1 + 2 * self.member_id)
        metrics = {
            FITNESS: validation_loss,
            "model_weight": self.weight.detach(),
            "shared_gradient": self._shared_gradient,
            "optimizer_lr": optimizer_lr,
            "training_target": training_target,
        }
        for name, value in metrics.items():
            self.log(name, value, on_step=False, on_epoch=True, sync_dist=False)

    def configure_optimizers(self):
        return torch.optim.SGD(self.parameters(), lr=1.0, momentum=0.9)


class ScalarClanTrainable(ClanLightningTrainable):
    """Supply ordinary model, data, controller, and Trainer construction."""

    def configure_controller(self, callbacks: RayControllerCallbacks) -> ClanController:
        initial_learning_rates = (0.05, 0.15)
        return ClanController(
            member_id=self.member_id,
            population_size=POPULATION_SIZE,
            initial_config={"lr": initial_learning_rates[self.member_id]},
            mutations={
                "lr": MutationSpec(
                    standard_deviation=0.02,
                    geometry="linear",
                    minimum=0.005,
                    maximum=0.25,
                )
            },
            mode="min",
            seed=2026,
            save_member_fitness=callbacks.save_member_fitness,
            load_population=callbacks.load_population,
            select_winner=callbacks.select_winner,
        )

    def configure_model(self) -> LightningModule:
        return ScalarRegression(member_id=self.member_id)

    def configure_dataloaders(self) -> tuple[DataLoader, DataLoader]:
        training_target = float(1 + 2 * self.member_id)
        train = TensorDataset(torch.ones(1, 1), torch.tensor([[training_target]]))
        validation = TensorDataset(torch.ones(1, 1), torch.zeros(1, 1))
        return DataLoader(train, batch_size=1), DataLoader(validation, batch_size=1)

    def configure_trainer(
        self,
        *,
        strategy: ClanDDPStrategy,
        callbacks: Sequence[Callback],
    ) -> Trainer:
        return Trainer(
            accelerator="cpu",
            devices=1,
            num_nodes=1,
            strategy=strategy,
            callbacks=list(callbacks),
            precision="bf16-mixed",
            max_steps=self.current_round_index + 1,
            max_epochs=self.current_round_index + 1,
            limit_train_batches=1,
            limit_val_batches=1,
            num_sanity_val_steps=0,
            use_distributed_sampler=False,
            logger=False,
            enable_checkpointing=False,
            enable_model_summary=False,
            enable_progress_bar=False,
        )

    def fitness_metric(self) -> str:
        return FITNESS

    def report_metrics(self) -> tuple[str, ...]:
        return OBSERVABILITY_METRICS


def build_tuner(*, rounds: int, storage_path: Path) -> Tuner:
    """Compose the manual Tune run after Ray has been initialized."""

    if rounds < 1:
        raise ValueError("rounds must be positive")
    available_cpus = ray.available_resources().get("CPU", 0.0)
    if available_cpus < POPULATION_SIZE:
        raise RuntimeError(
            f"the complete Clan requires {POPULATION_SIZE} concurrent CPUs; "
            f"Ray reports {available_cpus:g}"
        )

    member_ids = tuple(range(POPULATION_SIZE))
    exchange = RayClanRuntimeExchange.options(num_cpus=0).remote(
        member_ids=member_ids,
        timeout_s=60.0,
    )
    trainable = tune.with_resources(ScalarClanTrainable, {"cpu": 1})
    return Tuner(
        trainable,
        param_space={
            MEMBER_ID: tune.grid_search(member_ids),
            RUNTIME_EXCHANGE: exchange,
            NEXT_MEMBER_STATE: None,
        },
        tune_config=TuneConfig(
            scheduler=ClanTrialScheduler(final_round_index=rounds - 1),
            max_concurrent_trials=POPULATION_SIZE,
            reuse_actors=False,
        ),
        run_config=RunConfig(
            name="manual-clan-tuning",
            storage_path=str(storage_path.resolve()),
            verbose=1,
        ),
    )


def run(*, rounds: int, storage_path: Path):
    """Run the composition and return Tune's complete result grid."""

    if not ray.is_initialized():
        ray.init()
    results = build_tuner(rounds=rounds, storage_path=storage_path).fit()
    if results.errors:
        raise RuntimeError(f"Clan Tuning failed: {results.errors}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--storage-path", type=Path, default=Path("ray-results"))
    arguments = parser.parse_args()

    results = run(rounds=arguments.rounds, storage_path=arguments.storage_path)
    columns = [
        MEMBER_ID,
        ROUND_INDEX,
        "shared_gradient",
        "model_weight",
        FITNESS,
        WINNER_ID,
        f"{OPTIMIZER_CONFIG}/lr",
    ]
    for result in results:
        frame = result.metrics_dataframe
        visible_columns = [column for column in columns if column in frame]
        print(frame[visible_columns].sort_values(ROUND_INDEX).to_string(index=False))


if __name__ == "__main__":
    main()
