"""Ray Tune scheduler implementing the Clan single-parent generation transition."""

from __future__ import annotations

import copy
import random
from typing import Any, Callable
from uuid import uuid4

from ray.air.constants import TRAINING_ITERATION
from ray.tune.schedulers import PopulationBasedTraining

from clan_based_tuning.evolution import MutationSpec, select_winner_id
from clan_based_tuning.protocol import (
    CLAN_CHECKPOINT_SOURCE,
    CLAN_GENOME,
    CLAN_MEMBER_ID,
    CLAN_WINNER_ID,
)
from clan_based_tuning.runtime import (
    ClanRuntimeSpec,
    get_or_create_coordinator,
    wrap_function_trainable,
)


class ClanScheduler(PopulationBasedTraining):
    """Run Clan Tuning through Ray's synchronous PBT lifecycle.

    Tune remains responsible for trial execution, pausing, checkpoint registration,
    checkpoint reassignment, and restart. This scheduler replaces only PBT's population
    policy: every completed boundary has one selected parent, that parent's checkpoint is
    assigned to every next member, and each losing target receives a mutation of the
    parent's genome. The winning member retains the exact parent genome.

    Genome interpretation is deliberately outside this class. The resumed function
    trainable receives Ray's newly assigned genome and the user's own code applies it to
    the restored optimizer or other training state.
    """

    _supports_buffered_results = False

    def __init__(
        self,
        *,
        population_size: int,
        metric: str,
        mode: str,
        mutations: dict[str, MutationSpec],
        seed: int = 0,
        join_timeout_s: float = 120.0,
        poll_interval_s: float = 0.05,
    ) -> None:
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")
        if not mutations:
            raise ValueError("mutations must contain at least one controlled genome key")

        self.population_size = population_size
        self._mutations = dict(mutations)
        self._random = random.Random(seed)
        self._trial_ids: set[str] = set()
        self._member_ids: dict[str, int] = {}
        self._coordinator_handle = None
        self._runtime_spec = ClanRuntimeSpec(
            coordinator_name=f"clan-runtime-{uuid4().hex}",
            population_size=population_size,
            metric=metric,
            mode=mode,
            controlled_keys=tuple(self._mutations),
            join_timeout_s=join_timeout_s,
            poll_interval_s=poll_interval_s,
        )

        super().__init__(
            time_attr=TRAINING_ITERATION,
            metric=metric,
            mode=mode,
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

    def wrap(
        self,
        trainable: Callable[[dict[str, Any]], Any],
    ) -> Callable[[dict[str, Any]], Any]:
        """Return a function trainable whose user-visible argument remains only the genome."""

        return wrap_function_trainable(trainable, self._runtime_spec)

    def on_trial_add(self, tune_controller, trial) -> None:
        super().on_trial_add(tune_controller, trial)
        self._trial_ids.add(trial.trial_id)
        if len(self._trial_ids) > self.population_size:
            raise RuntimeError("Tune created more trials than ClanScheduler.population_size")

        if self._coordinator_handle is None:
            self._coordinator_handle = get_or_create_coordinator(self._runtime_spec)

        if len(self._trial_ids) == self.population_size:
            ordered = sorted(self._trial_ids)
            self._member_ids = {
                trial_id: member_id for member_id, trial_id in enumerate(ordered)
            }
            import ray

            ray.get(self._coordinator_handle.register_trials.remote(ordered))

    def on_trial_result(self, tune_controller, trial, result: dict[str, Any]) -> str:
        if len(self._member_ids) != self.population_size:
            raise RuntimeError(
                "the complete Clan was not created before a member reported; "
                "set num_samples and max_concurrent_trials to population_size and provide "
                "enough cluster resources for every member to run together"
            )
        return super().on_trial_result(tune_controller, trial, result)

    def _quantiles(self):
        """Present all losers as PBT targets and the sole Clan winner as the source."""

        reports = []
        for trial, state in self._trial_state.items():
            if trial.is_finished() or state.last_result is None:
                continue
            reports.append((trial, state.last_result))

        if len(reports) != self.population_size:
            return [], []

        by_member: dict[int, tuple[Any, dict[str, Any]]] = {}
        for trial, result in reports:
            try:
                member_id = int(result[CLAN_MEMBER_ID])
            except KeyError as error:
                raise RuntimeError("Clan result is missing stable member identity") from error
            expected_member = self._member_ids[trial.trial_id]
            if member_id != expected_member:
                raise RuntimeError("Clan result member identity disagrees with scheduler assignment")
            if member_id in by_member:
                raise RuntimeError("Clan boundary contains a duplicated member")
            by_member[member_id] = (trial, result)

        if set(by_member) != set(range(self.population_size)):
            raise RuntimeError("Clan boundary does not contain the complete configured population")

        fitnesses = [float(by_member[member_id][1][self._metric]) for member_id in range(self.population_size)]
        winner_id = select_winner_id(fitnesses, self._mode)

        for member_id, (trial, result) in by_member.items():
            if int(result[CLAN_WINNER_ID]) != winner_id:
                raise RuntimeError("worker and scheduler winner selection disagree")
            expected_checkpoint_source = member_id == winner_id
            if bool(result[CLAN_CHECKPOINT_SOURCE]) != expected_checkpoint_source:
                raise RuntimeError("Clan result reports the wrong checkpoint source")
            if result[CLAN_GENOME] != self._controlled_genome(trial.config):
                raise RuntimeError("reported producer genome disagrees with the active Tune config")

        winner_trial = by_member[winner_id][0]
        losers = [trial for member_id, (trial, _) in by_member.items() if member_id != winner_id]
        return losers, [winner_trial]

    def _get_new_config(self, trial, trial_to_clone):
        """Clone the selected genome and mutate only the scheduler-controlled keys."""

        del trial
        new_config = copy.deepcopy(trial_to_clone.config)
        operations = {}
        for key, mutation in self._mutations.items():
            old_value = new_config[key]
            new_config[key] = mutation.mutate(old_value, self._random)
            operations[key] = f"clan mutation: {old_value!r} -> {new_config[key]!r}"
        return new_config, operations

    def _controlled_genome(self, config: dict[str, Any]) -> dict[str, Any]:
        return {key: config[key] for key in self._mutations}

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_coordinator_handle"] = None
        return state


def _identity_config(config: dict[str, Any]) -> dict[str, Any]:
    return config
