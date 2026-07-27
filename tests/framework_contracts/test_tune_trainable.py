"""Contract tests for the Ray Trainable and Lightning window composition."""

from pathlib import Path

import pytest

pytest.importorskip("ray")
pytest.importorskip("lightning")

import torch

from clan_based_tuning import ClanController, MutationSpec
from clan_based_tuning.lightning_ddp import ClanProcessGroup
from clan_based_tuning.member_state import (
    CONTROLLER_STATE,
    NEXT_MEMBER_STATE,
    OPTIMIZER_CONFIG,
)
from clan_based_tuning.ray_exchange import PublishedRound
from clan_based_tuning.ray_transition import MEMBER_ID
from clan_based_tuning.tune_trainable import (
    RUNTIME_EXCHANGE,
    ClanLightningTrainable,
    ValidationRoundBoundary,
    resolve_process_group,
)

pytestmark = [pytest.mark.framework_contract, pytest.mark.requires_ray]


class RemoteCall:
    def __init__(self, call):
        self._call = call

    def remote(self, *args, **kwargs):
        return self._call(*args, **kwargs)


class FakeRuntimeExchange:
    def __init__(self):
        self.published = []
        self.announcements = []
        self.publish = RemoteCall(self._publish)
        self.load = RemoteCall(self._load)
        self.announce = RemoteCall(self._announce)
        self.join_process_group = RemoteCall(self._join_process_group)

    def _publish(self, round_):
        self.published.append(round_)

    def _load(self, round_index):
        return [
            PublishedRound(0, round_index, {"lr": 0.1}, 0.0),
            PublishedRound(1, round_index, {"lr": 0.2}, 1.0),
        ]

    def _announce(self, **announcement):
        self.announcements.append(announcement)

    def _join_process_group(self, **request):
        return ClanProcessGroup(
            session_id=3,
            global_rank=request["member_id"],
            world_size=2,
            master_address=request["host"],
            master_port=request["port"],
        )


class FakeTrainer:
    def __init__(self, *, strategy, callbacks):
        self.strategy = strategy
        self.callbacks = list(callbacks)
        self.callback_metrics = {"fitness": torch.tensor(0.0)}
        self.sanity_checking = False
        self.should_stop = False
        parameter = torch.nn.Parameter(torch.ones(1))
        self.optimizers = [torch.optim.SGD([parameter], lr=9.0)]
        self.ckpt_path = None

    def fit(self, model, *, train_dataloaders, val_dataloaders, ckpt_path):
        del train_dataloaders, val_dataloaders
        self.ckpt_path = ckpt_path
        for callback in self.callbacks:
            callback.on_train_start(self, model)
        for callback in self.callbacks:
            callback.on_validation_end(self, model)


class FakeClanTrainable(ClanLightningTrainable):
    def configure_controller(self, callbacks):
        return ClanController(
            member_id=self._member_id,
            population_size=2,
            initial_config={"lr": 0.1},
            mutations={
                "lr": MutationSpec(
                    standard_deviation=0.0,
                    geometry="linear",
                    minimum=0.0,
                    maximum=10.0,
                )
            },
            mode="min",
            seed=17,
            save_member_fitness=callbacks.save_member_fitness,
            load_population=callbacks.load_population,
            select_winner=callbacks.select_winner,
        )

    def configure_model(self):
        return object()

    def configure_dataloaders(self):
        return object(), object()

    def configure_trainer(self, *, strategy, callbacks):
        return FakeTrainer(strategy=strategy, callbacks=callbacks)

    def fitness_metric(self):
        return "fitness"

    def join_process_group(self):
        return ClanProcessGroup(
            session_id=3,
            global_rank=self._member_id,
            world_size=2,
            master_address="127.0.0.1",
            master_port=4321,
        )

    @staticmethod
    def resolve_actor_call(value):
        return value


def test_validation_boundary_ignores_sanity_and_stops_after_local_result():
    boundary = ValidationRoundBoundary(
        fitness_metric="fitness",
        report_metrics=("fitness", "other"),
    )

    class TrainerState:
        def __init__(self):
            self.sanity_checking = True
            self.callback_metrics = {"fitness": torch.tensor(1.0), "other": 2.0}
            self.should_stop = False

    trainer = TrainerState()
    boundary.on_validation_end(trainer, None)
    with pytest.raises(RuntimeError, match="without a qualifying"):
        boundary.result()

    trainer.sanity_checking = False
    boundary.on_validation_end(trainer, None)
    assert boundary.result() == {"fitness": 1.0, "other": 2.0}
    assert trainer.should_stop


def test_process_group_resolution_supplies_fresh_member_local_request():
    exchange = FakeRuntimeExchange()
    group = resolve_process_group(
        exchange=exchange,
        member_id=0,
        resolve=lambda value: value,
        host_address=lambda: "10.0.0.1",
        reserve_port=lambda: 4321,
        make_token=lambda: "fresh-token",
    )

    assert group == ClanProcessGroup(
        session_id=3,
        global_rank=0,
        world_size=2,
        master_address="10.0.0.1",
        master_port=4321,
    )


def test_trainable_step_runs_one_window_and_returns_local_transition(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "ray.tune.trainable.trainable.DEFAULT_STORAGE_PATH",
        str(tmp_path),
    )
    exchange = FakeRuntimeExchange()
    trainable = FakeClanTrainable(
        config={
            MEMBER_ID: 0,
            RUNTIME_EXCHANGE: exchange,
            NEXT_MEMBER_STATE: None,
        }
    )

    result = trainable.step()

    assert result["fitness"] == 0.0
    assert result[MEMBER_ID] == 0
    assert result["clan_winner_id"] == 0
    assert result["clan_controller_state"]["round_index"] == 1
    assert trainable._exchange.announcements == [{"round_index": 0, "member_id": 0, "winner_id": 0}]


def test_trainable_load_checkpoint_requires_lightning_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ray.tune.trainable.trainable.DEFAULT_STORAGE_PATH",
        str(tmp_path),
    )
    exchange = FakeRuntimeExchange()
    trainable = FakeClanTrainable(
        config={
            MEMBER_ID: 0,
            RUNTIME_EXCHANGE: exchange,
            NEXT_MEMBER_STATE: None,
        }
    )

    with pytest.raises(RuntimeError, match="no Lightning"):
        trainable.load_checkpoint(str(tmp_path))

    Path(tmp_path, "lightning.ckpt").touch()
    trainable.load_checkpoint(str(tmp_path))
    assert trainable._checkpoint_path == Path(tmp_path, "lightning.ckpt")


def test_recreated_actor_uses_assigned_controller_round(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ray.tune.trainable.trainable.DEFAULT_STORAGE_PATH",
        str(tmp_path),
    )
    exchange = FakeRuntimeExchange()
    prior = FakeClanTrainable(
        config={
            MEMBER_ID: 0,
            RUNTIME_EXCHANGE: exchange,
            NEXT_MEMBER_STATE: None,
        }
    )
    first_result = prior.step()
    assigned_state = {
        CONTROLLER_STATE: first_result[CONTROLLER_STATE],
        OPTIMIZER_CONFIG: first_result[OPTIMIZER_CONFIG],
    }
    recreated = FakeClanTrainable(
        config={
            MEMBER_ID: 0,
            RUNTIME_EXCHANGE: exchange,
            NEXT_MEMBER_STATE: assigned_state,
        }
    )

    second_result = recreated.step()

    assert second_result["clan_round_index"] == 1
    assert second_result[CONTROLLER_STATE]["round_index"] == 2
