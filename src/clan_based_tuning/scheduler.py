"""Ray Tune scheduler adapter implementing the Clan generation transition.

The scheduler uses Tune's ordinary ``TrialScheduler`` lifecycle but owns its synchronous
single-parent transition rather than subclassing Ray's PBT implementation. The algorithmic
choice of winner and child genomes is delegated to the framework-independent evolution
module. A narrow ``ray_compat`` module owns the few Tune-internal checkpoint/config transfer
operations for which Ray does not expose a stable public atomic operation.

The synchronous control flow is intentionally derived from Ray Tune's PBT behavior: pause
members at a common reported boundary, capture the selected checkpoint, replace every
member's continuation, then allow FIFO scheduling to resume them. Unlike general PBT, this
module has no asynchronous mode, quantiles, resampling policy, or independent parent choice.
"""

import logging
import random
from collections.abc import Callable, Mapping
from typing import Any
from uuid import uuid4

from ray.air.constants import TRAINING_ITERATION
from ray.tune import Checkpoint
from ray.tune.experiment import Trial
from ray.tune.schedulers import FIFOScheduler, TrialScheduler

from clan_based_tuning.cohort import ClanRuntimeSpec
from clan_based_tuning.evolution import build_mutation_rules, resolve_generation
from clan_based_tuning.protocol import (
    CLAN_CHECKPOINT_SOURCE,
    CLAN_MEMBER_ID,
    CLAN_WINNER_ID,
)
from clan_based_tuning.ray_compat import (
    assign_trial_continuation,
    capture_trial_checkpoint,
    pause_trial_without_checkpoint,
)
from clan_based_tuning.runtime import (
    build_runtime_spec,
    register_runtime_assignment,
    release_runtime_assignment,
)

_LOGGER = logging.getLogger(__name__)
_RuntimeRegistrar = Callable[
    [ClanRuntimeSpec, list[str], Any | None, Any | None],
    tuple[Any, Any],
]
_RuntimeReleaser = Callable[[ClanRuntimeSpec, list[str], Any | None, Any | None], None]
_MutationBuilder = Callable[[Mapping[str, Mapping[str, Any]]], Any]
_GenerationResolver = Callable[..., Any]
_CheckpointCapture = Callable[[Any, Trial, dict[str, Any]], Checkpoint]
_TrialPause = Callable[[Any, Trial], None]
_ContinuationAssigner = Callable[[Trial, dict[str, Any], Checkpoint, dict[str, Any]], None]


# Main


class ClanScheduler(FIFOScheduler):
    """Run synchronous single-parent Clan evolution through Ray Tune.

    Ray remains responsible for trial execution, resources, pausing/resuming, storage, and
    function invocation. This scheduler adds the Clan-specific generation barrier: every
    member reports the same boundary, one parent is selected, and every next member receives
    the same parent checkpoint plus an independent mutation of that parent's Tune config.

    The implementation intentionally does not subclass ``PopulationBasedTraining``. CBT
    owns the small synchronous transition it needs so future Ray PBT refactors cannot change
    Clan semantics. ``ray_compat`` isolates the remaining low-level Tune transfer operations,
    while runtime actor construction/release is injected from the runtime construction layer.

    Args:
        population_size: Number of concurrently resident Clan members. Tune must create
            exactly this many trials and sufficient Ray resources must exist for all members
            to run together.
        mutations: Mapping from user Tune-config keys to scalar mutation dictionaries. CBT
            mutates values only; user code owns their meaning and application.
        seed: Seed for the scheduler-owned mutation random stream.
        join_timeout_s: Maximum seconds a member waits for the complete Clan rendezvous.
        poll_interval_s: Poll interval used while members rendezvous.
        _mutation_builder: Injectable mutation-rule construction function.
        _generation_resolver: Injectable complete-generation policy function.
        _checkpoint_capture: Injectable selected-boundary checkpoint operation.
        _pause_trial: Injectable Tune pause operation used during the transition.
        _assign_continuation: Injectable Tune continuation assignment operation.
        _runtime_spec_builder: Injectable construction function for immutable runtime facts.
        _runtime_registrar: Injectable operation that creates/reuses and registers Ray actors.
        _runtime_releaser: Injectable operation that removes a completed runtime assignment.

    Raises:
        ValueError: If population or mutation/rendezvous configuration is invalid.

    Notes:
        Scientifically valid Clan variation may affect only choices applied after the common
        gradient has been computed, normally optimizer-side update policy. CBT deliberately
        does not infer or enforce the meaning of config keys.
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
        _mutation_builder: _MutationBuilder = build_mutation_rules,
        _generation_resolver: _GenerationResolver = resolve_generation,
        _checkpoint_capture: _CheckpointCapture = capture_trial_checkpoint,
        _pause_trial: _TrialPause = pause_trial_without_checkpoint,
        _assign_continuation: _ContinuationAssigner = assign_trial_continuation,
        _runtime_spec_builder: Callable[..., ClanRuntimeSpec] = build_runtime_spec,
        _runtime_registrar: _RuntimeRegistrar = register_runtime_assignment,
        _runtime_releaser: _RuntimeReleaser = release_runtime_assignment,
    ) -> None:
        if population_size < 2:
            raise ValueError("population_size must be at least two")
        if not mutations:
            raise ValueError("mutations must contain at least one genome key")
        if join_timeout_s <= 0:
            raise ValueError("join_timeout_s must be positive")
        if poll_interval_s <= 0:
            raise ValueError("poll_interval_s must be positive")

        super().__init__()
        self.population_size = population_size
        self._mutations = _mutation_builder(mutations)
        self._random = random.Random(seed)
        self._generation_resolver = _generation_resolver
        self._checkpoint_capture = _checkpoint_capture
        self._pause_trial = _pause_trial
        self._assign_continuation = _assign_continuation
        self._mode: str | None = None
        self._trial_ids: set[str] = set()
        self._member_ids: dict[str, int] = {}
        self._reports: dict[str, dict[str, Any]] = {}
        self._finished_trial_ids: set[str] = set()
        self._completed_boundary = 0
        self._coordinator_name = f"clan-runtime-{uuid4().hex}"
        self._join_timeout_s = float(join_timeout_s)
        self._poll_interval_s = float(poll_interval_s)
        self._runtime_spec_builder = _runtime_spec_builder
        self._runtime_registrar = _runtime_registrar
        self._runtime_releaser = _runtime_releaser
        self._runtime_spec: ClanRuntimeSpec | None = None
        self._coordinator_handle: Any | None = None
        self._registry_handle: Any | None = None
        self._runtime_registered = False

    def set_search_properties(self, metric: str | None, mode: str | None, **spec: Any) -> bool:
        """Receive Tune's metric/mode and retain the Clan selection direction."""

        if metric is None:
            raise ValueError("ClanScheduler requires tune.TuneConfig(metric=...)")
        if mode not in {"min", "max"}:
            raise ValueError("ClanScheduler requires tune.TuneConfig(mode='min' or 'max')")

        accepted = super().set_search_properties(metric, mode, **spec)
        self._mode = mode
        return accepted

    def on_trial_add(self, tune_controller: Any, trial: Trial) -> None:
        """Register stable member identity once Tune has created the complete population."""

        super().on_trial_add(tune_controller, trial)
        if self.metric is None or self._mode is None:
            raise RuntimeError("Tune did not configure the Clan metric and mode before trials")

        self._trial_ids.add(trial.trial_id)
        if len(self._trial_ids) > self.population_size:
            raise RuntimeError("Tune created more trials than ClanScheduler.population_size")

        if len(self._trial_ids) != self.population_size:
            return

        ordered = sorted(self._trial_ids)
        self._member_ids = {trial_id: member_id for member_id, trial_id in enumerate(ordered)}

        experiment_names = {
            candidate.experiment_dir_name
            for candidate in tune_controller.get_trials()
            if candidate.trial_id in self._member_ids
        }
        if len(experiment_names) != 1:
            raise RuntimeError("one Clan population must belong to exactly one Tune experiment")

        experiment_name = experiment_names.pop()
        self._runtime_spec = self._runtime_spec_builder(
            coordinator_name=self._coordinator_name,
            experiment_name=experiment_name,
            population_size=self.population_size,
            metric=self.metric,
            mode=self._mode,
            join_timeout_s=self._join_timeout_s,
            poll_interval_s=self._poll_interval_s,
        )
        self._register_runtime()
        _LOGGER.info(
            "Clan cohort registered experiment=%s population=%d members=%s",
            experiment_name,
            self.population_size,
            ordered,
        )

    def choose_trial_to_run(self, tune_controller: Any) -> Trial | None:
        """Launch only a complete Clan and never mix two generation boundaries."""

        if len(self._member_ids) != self.population_size:
            return None
        if self._reports:
            # Once the first member reports a boundary, early reporters are paused. Resuming
            # one before the remaining live members report would mix two generations in the
            # runtime rendezvous. Keep every paused member gated until the complete transition
            # clears `_reports`.
            return None
        self._register_runtime()
        return super().choose_trial_to_run(tune_controller)

    def on_trial_result(
        self,
        tune_controller: Any,
        trial: Trial,
        result: dict[str, Any],
    ) -> str:
        """Pause at the boundary and replace the complete population once all members report."""

        if len(self._member_ids) != self.population_size:
            raise RuntimeError(
                "the complete Clan was not created before a member reported; create exactly "
                "population_size trials and provision enough resources for every member"
            )
        self._register_runtime()
        self._validate_report_identity(trial, result)

        try:
            boundary = int(result[TRAINING_ITERATION])
        except KeyError as error:
            raise RuntimeError("Clan result is missing Tune training_iteration") from error
        if boundary <= self._completed_boundary:
            raise RuntimeError("Clan member reported a generation boundary that already completed")
        if trial.trial_id in self._reports:
            raise RuntimeError("Clan boundary contains a duplicated member report")

        self._reports[trial.trial_id] = result
        _LOGGER.debug(
            "Clan boundary report boundary=%d member=%d reports=%d/%d",
            boundary,
            self._member_ids[trial.trial_id],
            len(self._reports),
            self.population_size,
        )
        if len(self._reports) < self.population_size:
            return TrialScheduler.PAUSE

        boundaries = {int(report[TRAINING_ITERATION]) for report in self._reports.values()}
        if len(boundaries) != 1:
            raise RuntimeError("Clan members reported different generation boundaries")
        completed_boundary = boundaries.pop()

        ordered_trials = self._ordered_trials(tune_controller)
        ordered_reports = [self._reports[candidate.trial_id] for candidate in ordered_trials]
        decision = self._generation_resolver(
            fitnesses=[float(report[self.metric]) for report in ordered_reports],
            configs=[candidate.config for candidate in ordered_trials],
            mode=self._require_mode(),
            mutations=self._mutations,
            random_stream=self._random,
        )
        self._validate_worker_decision(ordered_reports, decision.winner_id)

        winner_trial = ordered_trials[decision.winner_id]
        winner_report = ordered_reports[decision.winner_id]
        checkpoint = self._checkpoint_capture(tune_controller, winner_trial, winner_report)

        # Ray's scheduler callback may still be executing inside one running trial. Pause every
        # member without creating another checkpoint, then make one explicit continuation the
        # authoritative state for the entire next generation.
        for candidate in ordered_trials:
            self._pause_trial(tune_controller, candidate)
        for member_id, candidate in enumerate(ordered_trials):
            self._assign_continuation(
                candidate,
                decision.child_configs[member_id],
                checkpoint,
                winner_report,
            )

        mutation_keys = tuple(self._mutations)
        parent_genome = {key: decision.parent_config[key] for key in mutation_keys}
        child_genomes = [
            {key: child[key] for key in mutation_keys} for child in decision.child_configs
        ]
        _LOGGER.info(
            "Clan generation resolved boundary=%d winner=%d parent=%s children=%s",
            completed_boundary,
            decision.winner_id,
            parent_genome,
            child_genomes,
        )

        self._completed_boundary = completed_boundary
        self._reports = {}
        return TrialScheduler.NOOP if trial.status == Trial.PAUSED else TrialScheduler.PAUSE

    def on_trial_complete(
        self,
        tune_controller: Any,
        trial: Trial,
        result: dict[str, Any],
    ) -> None:
        """Release runtime actors after every member of the successful population completes."""

        super().on_trial_complete(tune_controller, trial, result)
        if trial.trial_id not in self._trial_ids:
            return

        self._finished_trial_ids.add(trial.trial_id)
        if self._finished_trial_ids == self._trial_ids:
            self._release_runtime()

    def debug_string(self) -> str:
        """Return a concise scheduler description for Tune console output."""

        return "Using Clan synchronous single-parent scheduling."

    def _validate_report_identity(self, trial: Trial, result: dict[str, Any]) -> None:
        """Require worker-reported stable member identity to match scheduler assignment."""

        try:
            member_id = int(result[CLAN_MEMBER_ID])
        except KeyError as error:
            raise RuntimeError("Clan result is missing stable member identity") from error

        expected_member = self._member_ids[trial.trial_id]
        if member_id != expected_member:
            raise RuntimeError("Clan result member identity disagrees with scheduler assignment")

    def _validate_worker_decision(
        self,
        ordered_reports: list[dict[str, Any]],
        winner_id: int,
    ) -> None:
        """Require every worker to agree with the driver's winner and checkpoint source."""

        for member_id, report in enumerate(ordered_reports):
            if int(report[CLAN_WINNER_ID]) != winner_id:
                raise RuntimeError("worker and scheduler winner selection disagree")
            expected_checkpoint_source = member_id == winner_id
            if bool(report[CLAN_CHECKPOINT_SOURCE]) != expected_checkpoint_source:
                raise RuntimeError("Clan result reports the wrong checkpoint source")

    def _ordered_trial_ids(self) -> list[str]:
        """Return registered Tune trial IDs in stable Clan member-ID order."""

        return [
            trial_id
            for trial_id, _member_id in sorted(
                self._member_ids.items(),
                key=lambda item: item[1],
            )
        ]

    def _ordered_trials(self, tune_controller: Any) -> list[Trial]:
        """Return live Tune trial objects in stable Clan member-ID order."""

        by_id = {
            candidate.trial_id: candidate
            for candidate in tune_controller.get_trials()
            if candidate.trial_id in self._member_ids
        }
        if set(by_id) != set(self._member_ids):
            raise RuntimeError("Tune controller does not contain the complete registered Clan")
        return [by_id[trial_id] for trial_id in self._ordered_trial_ids()]

    def _require_mode(self) -> str:
        """Return the configured Tune selection mode after scheduler setup."""

        if self._mode is None:
            raise RuntimeError("Tune did not configure the Clan selection mode")
        return self._mode

    def _register_runtime(self) -> None:
        """Register one complete runtime assignment once per live scheduler process."""

        if self._runtime_registered:
            return
        if len(self._member_ids) != self.population_size or self._runtime_spec is None:
            return

        self._registry_handle, self._coordinator_handle = self._runtime_registrar(
            self._runtime_spec,
            self._ordered_trial_ids(),
            self._registry_handle,
            self._coordinator_handle,
        )
        self._runtime_registered = True

    def _release_runtime(self) -> None:
        """Remove one completed assignment and terminate its scheduler-owned coordinator."""

        if self._runtime_spec is None or not self._runtime_registered:
            return

        self._runtime_releaser(
            self._runtime_spec,
            self._ordered_trial_ids(),
            self._registry_handle,
            self._coordinator_handle,
        )
        self._registry_handle = None
        self._coordinator_handle = None
        self._runtime_registered = False
        _LOGGER.info("Clan runtime released experiment=%s", self._runtime_spec.experiment_name)

    def __getstate__(self) -> dict[str, Any]:
        """Strip live actor handles while preserving restorable scheduler authority."""

        state = self.__dict__.copy()
        state["_coordinator_handle"] = None
        state["_registry_handle"] = None
        state["_runtime_registered"] = False
        return state
