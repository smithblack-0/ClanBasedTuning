"""Ray Tune scheduler implementing the Clan single-parent generation transition."""

from __future__ import annotations

import copy
import random
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ray.air.constants import TRAINING_ITERATION
from ray.tune.schedulers import PopulationBasedTraining

from clan_based_tuning.evolution import _MutationRule, select_winner_id
from clan_based_tuning.protocol import (
    CLAN_CHECKPOINT_SOURCE,
    CLAN_MEMBER_ID,
    CLAN_WINNER_ID,
)
from clan_based_tuning.runtime import (
    ClanRuntimeSpec,
    get_or_create_coordinator,
    get_or_create_registry,
)


class ClanScheduler(PopulationBasedTraining):
    """Run Clan Tuning through Ray's synchronous PBT execution lifecycle.

    Ray remains responsible for trial execution, resources, pausing, checkpoint transfer,
    restoration, and config replacement. This scheduler changes only the population policy:
    one selected member is the parent for the whole next generation and every next member
    receives an independent mutation of that parent's Tune config.

    Configure the optimization metric and direction through ``tune.TuneConfig(metric=...,
    mode=...)`` like other Ray schedulers. ``mutations`` is a mapping from Tune-config keys
    to plain dictionaries with ``standard_deviation``, ``geometry`` (``"linear"`` or
    ``"log"``), ``minimum``, and ``maximum``.

    Args:
        population_size: Number of concurrently resident Clan members. The Tune run must
            create exactly this many trials and the cluster must have resources for all of
            them at once.
        mutations: Mutation rules for the Tune-config values that may vary between Clan
            members. CBT mutates values only; user code owns their meaning and application.
        seed: Seed for the scheduler-owned mutation random stream.
        join_timeout_s: Maximum seconds a member waits for the complete Clan rendezvous.
        poll_interval_s: Poll interval used while members rendezvous.

    Raises:
        ValueError: If population or mutation configuration is invalid.

    Notes:
        A scientifically valid Clan genome may vary only choices applied after the shared
        gradient has been computed (normally optimizer-side policy). CBT deliberately does
        not infer or enforce what config keys mean.
    """

    _supports_buffered_results = False

    def __init__(
        self,
        *,
        population_size: int,
        mutations: Mapping[str, Mapping[str, Any]],
        seed: int = 0,
        join_timeout_s: float = 120.0,
        poll_interval_s: float = 0.05,
    ) -> None:
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        if not mutations:
            raise ValueError("mutations must contain at least one genome key")
        if join_timeout_s <= 0:
            raise ValueError("join_timeout_s must be positive")
        if poll_interval_s <= 0:
            raise ValueError("poll_interval_s must be positive")

        self.population_size = population_size
        self._mutations = {
            key: _MutationRule.from_config(rule) for key, rule in mutations.items()
        }
        self._random = random.Random(seed)
        self._trial_ids: set[str] = set()
        self._member_ids: dict[str, int] = {}
        self._parent_config: dict[str, Any] | None = None
        self._coordinator_name = f"clan-runtime-{uuid4().hex}"
        self._join_timeout_s = float(join_timeout_s)
        self._poll_interval_s = float(poll_interval_s)
        self._runtime_spec: ClanRuntimeSpec | None = None
        self._coordinator_handle = None
        self._registry_handle = None

        super().__init__(
            time_attr=TRAINING_ITERATION,
            metric=None,
            mode=None,
            perturbation_interval=1,
            burn_in_period=0,
            hyperparam_mutations={},
            quantile_fraction=0.5,
            resample_probability=0.0,
            custom_explore_fn=_identity_config,
            log_config=False,
            require_attrs=True,
            synch=True,
        )

    def set_search_properties(self, metric: str | None, mode: str | None, **spec) -> bool:
        """Receive the ordinary Tune metric/mode and make them available to members."""

        if metric is None:
            raise ValueError("ClanScheduler requires tune.TuneConfig(metric=...)")
        if mode not in {"min", "max"}:
            raise ValueError("ClanScheduler requires tune.TuneConfig(mode='min' or 'max')")

        accepted = super().set_search_properties(metric, mode, **spec)
        self._runtime_spec = ClanRuntimeSpec(
            coordinator_name=self._coordinator_name,
            population_size=self.population_size,
            metric=metric,
            mode=mode,
            join_timeout_s=self._join_timeout_s,
            poll_interval_s=self._poll_interval_s,
        )
        return accepted

    def on_trial_add(self, tune_controller, trial) -> None:
        self._require_runtime_spec()
        super().on_trial_add(tune_controller, trial)
        self._trial_ids.add(trial.trial_id)
        if len(self._trial_ids) > self.population_size:
            raise RuntimeError("Tune created more trials than ClanScheduler.population_size")

        if len(self._trial_ids) == self.population_size:
            ordered = sorted(self._trial_ids)
            self._member_ids = {trial_id: member_id for member_id, trial_id in enumerate(ordered)}
            self._register_runtime()

    def choose_trial_to_run(self, tune_controller):
        """Re-establish runtime actors before Ray launches or restores a member."""

        self._register_runtime()
        return super().choose_trial_to_run(tune_controller)

    def on_trial_result(self, tune_controller, trial, result: dict[str, Any]) -> str:
        if len(self._member_ids) != self.population_size:
            raise RuntimeError(
                "the complete Clan was not created before a member reported; create exactly "
                "population_size trials and provide enough resources for every member "
                "to run together"
            )
        self._register_runtime()
        return super().on_trial_result(tune_controller, trial, result)

    def _quantiles(self):
        """Present every loser as a PBT target and the sole Clan winner as source."""

        reports = []
        for trial, state in self._trial_state.items():
            if trial.is_finished() or state.last_result is None:
                continue
            reports.append((trial, state.last_result))

        if len(reports) != self.population_size:
            return [], []

        by_member: dict[int, tuple[Any, dict[str, Any]]] = {}
        iterations = set()
        for trial, result in reports:
            try:
                member_id = int(result[CLAN_MEMBER_ID])
            except KeyError as error:
                raise RuntimeError("Clan result is missing stable member identity") from error

            expected_member = self._member_ids[trial.trial_id]
            if member_id != expected_member:
                raise RuntimeError(
                    "Clan result member identity disagrees with scheduler assignment"
                )
            if member_id in by_member:
                raise RuntimeError("Clan boundary contains a duplicated member")

            by_member[member_id] = (trial, result)
            iterations.add(int(result[TRAINING_ITERATION]))

        if set(by_member) != set(range(self.population_size)):
            raise RuntimeError("Clan boundary does not contain the complete configured population")
        if len(iterations) != 1:
            raise RuntimeError("Clan members reported different generation boundaries")

        if self._metric is None or self._mode is None:
            raise RuntimeError("Tune did not configure the Clan metric and mode")
        fitnesses = [
            float(by_member[member_id][1][self._metric])
            for member_id in range(self.population_size)
        ]
        winner_id = select_winner_id(fitnesses, self._mode)

        for member_id, (_, result) in by_member.items():
            if int(result[CLAN_WINNER_ID]) != winner_id:
                raise RuntimeError("worker and scheduler winner selection disagree")
            expected_checkpoint_source = member_id == winner_id
            if bool(result[CLAN_CHECKPOINT_SOURCE]) != expected_checkpoint_source:
                raise RuntimeError("Clan result reports the wrong checkpoint source")

        winner_trial = by_member[winner_id][0]
        self._parent_config = copy.deepcopy(winner_trial.config)
        losers = [trial for member_id, (trial, _) in by_member.items() if member_id != winner_id]
        return losers, [winner_trial]

    def _checkpoint_or_exploit(self, trial, tune_controller, upper_quantile, lower_quantile):
        """Use PBT transfer, then give the selected source its own next mutation too."""

        super()._checkpoint_or_exploit(trial, tune_controller, upper_quantile, lower_quantile)
        if trial in upper_quantile:
            new_config, _ = self._get_new_config(trial, trial)
            trial.set_config(new_config)

    def _get_new_config(self, trial, trial_to_clone):
        """Mutate a fresh copy of the selected round parent's Tune config."""

        del trial, trial_to_clone
        if self._parent_config is None:
            raise RuntimeError("Clan parent config was not resolved before mutation")

        new_config = copy.deepcopy(self._parent_config)
        operations = {}
        for key, mutation in self._mutations.items():
            if key not in new_config:
                raise KeyError(f"Clan mutation key {key!r} is missing from the Tune config")
            old_value = new_config[key]
            new_config[key] = mutation.mutate(old_value, self._random)
            operations[key] = f"clan mutation: {old_value!r} -> {new_config[key]!r}"
        return new_config, operations

    def _require_runtime_spec(self) -> ClanRuntimeSpec:
        runtime_spec = self._runtime_spec
        if runtime_spec is None:
            raise RuntimeError(
                "ClanScheduler has no metric/mode; configure both on tune.TuneConfig"
            )
        return runtime_spec

    def _register_runtime(self) -> None:
        if len(self._member_ids) != self.population_size:
            return

        import ray

        runtime_spec = self._require_runtime_spec()
        if self._registry_handle is None:
            self._registry_handle = get_or_create_registry()
        if self._coordinator_handle is None:
            self._coordinator_handle = get_or_create_coordinator(runtime_spec)

        ordered = [
            trial_id for trial_id, _ in sorted(self._member_ids.items(), key=lambda item: item[1])
        ]
        ray.get(self._coordinator_handle.register_trials.remote(ordered))
        ray.get(self._registry_handle.register_trials.remote(ordered, runtime_spec))

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_coordinator_handle"] = None
        state["_registry_handle"] = None
        return state


def _identity_config(config: dict[str, Any]) -> dict[str, Any]:
    return config
