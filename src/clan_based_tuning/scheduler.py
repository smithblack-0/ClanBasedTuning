"""Ray Tune scheduler adapter implementing the Clan generation transition.

The scheduler uses Tune's ordinary ``TrialScheduler`` lifecycle but owns the synchronous
single-parent transition that stock PBT cannot express without private-policy coupling. Pure
selection/mutation lives in ``evolution``; Ray checkpoint/config transfer lives in
``ray_compat``; runtime actor construction lives in ``runtime``. This module's job is to keep
those pieces in one coherent generation state machine without becoming a second Tune runtime.

The critical scheduling invariant is that generations never overlap. Once any member reports
a boundary, no paused member may resume until every member has reported, the parent checkpoint
has been selected, and all child continuations have been assigned.
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
from clan_based_tuning.evolution import build_mutation_rule, resolve_generation
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
_MutationRuleBuilder = Callable[[Mapping[str, Any]], Any]
_GenerationResolver = Callable[..., Any]
_CheckpointCapture = Callable[[Any, Trial, dict[str, Any]], Checkpoint]
_TrialPause = Callable[[Any, Trial], None]
_ContinuationAssigner = Callable[[Trial, dict[str, Any], Checkpoint, dict[str, Any]], None]


# Main


class ClanScheduler(FIFOScheduler):
    """Add a complete-population Clan generation barrier to Ray Tune.

    Ray still owns trial execution, resources, storage, pause/resume mechanics, and function
    invocation. This object owns only the cross-trial decision that Ray cannot make for CBT:
    wait for one report from every stable member, select one parent, capture that member's
    checkpoint, and assign independently mutated children of the same parent to every member.

    Stable member IDs are derived from sorted Tune trial IDs only after the complete configured
    population exists. That ordering is reused for fitness comparison and child mutation so a
    serialized RNG state produces the same sibling assignment regardless of Tune callback
    order.

    Args:
        population_size: Number of concurrently resident Clan members. Tune must create
            exactly this many trials and sufficient Ray resources must exist for all members
            to run together.
        mutations: Mapping from user Tune-config keys to scalar mutation dictionaries. CBT
            mutates values only; user code owns their meaning and application.
        seed: Seed for the scheduler-owned mutation stream. Its state is serialized with the
            scheduler so restored experiments continue the same mutation sequence.
        join_timeout_s: Maximum time a worker waits for the complete cross-trial rendezvous.
        poll_interval_s: Poll cadence used by the worker-side rendezvous.
        _mutation_rule_builder: Replacement rule constructor; it must preserve the validated
            scalar-mutation contract used by ``resolve_generation``.
        _generation_resolver: Replacement pure generation policy for isolated composition
            tests; production uses ``resolve_generation``.
        _checkpoint_capture: Ray compatibility operation that materializes the selected
            boundary checkpoint.
        _pause_trial: Ray compatibility operation that pauses without creating a second save.
        _assign_continuation: Ray compatibility operation that installs one child's config and
            the selected parent checkpoint.
        _runtime_spec_builder: Construction seam that keeps runtime namespace/actor facts out
            of scheduler policy.
        _runtime_registrar: Runtime lifecycle operation used both initially and after restore.
        _runtime_releaser: Successful-completion cleanup for the scheduler-owned cohort actor.

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
        _mutation_rule_builder: _MutationRuleBuilder = build_mutation_rule,
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
        self._mutations = {
            key: _mutation_rule_builder(config) for key, config in mutations.items()
        }
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
        """Capture the selection contract Tune supplies after scheduler construction.

        ``FIFOScheduler`` retains the metric but not the Clan selection direction, so CBT keeps
        ``mode`` explicitly. Rejecting missing values here prevents workers from joining a
        cohort whose driver cannot later reproduce their winner decision.
        """

        if metric is None:
            raise ValueError("ClanScheduler requires tune.TuneConfig(metric=...)")
        if mode not in {"min", "max"}:
            raise ValueError("ClanScheduler requires tune.TuneConfig(mode='min' or 'max')")

        accepted = super().set_search_properties(metric, mode, **spec)
        self._mode = mode
        return accepted

    def on_trial_add(self, tune_controller: Any, trial: Trial) -> None:
        """Freeze stable member IDs only when Tune has created the complete population.

        Assigning IDs incrementally would make ranks depend on trial-creation callback order.
        Waiting for the complete set and sorting Tune trial IDs gives every later subsystem a
        deterministic member order for DDP ranks, fitnesses, and seeded sibling mutations.
        """

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
        """Delegate to FIFO only when doing so cannot create a mixed-generation DDP world.

        Before all IDs are known, starting a member would let it rendezvous without a complete
        topology. After the first boundary report, early reporters are paused; resuming one
        before the remaining members report would put that process in generation N+1 while
        peers are still finishing generation N. Both states therefore intentionally return no
        runnable trial.
        """

        if len(self._member_ids) != self.population_size:
            return None
        if self._reports:
            return None
        self._register_runtime()
        return super().choose_trial_to_run(tune_controller)

    def on_trial_result(
        self,
        tune_controller: Any,
        trial: Trial,
        result: dict[str, Any],
    ) -> str:
        """Resolve one atomic Clan generation transition after the last member reports.

        Early reporters are paused and retained in ``_reports``. The final report must agree
        on Tune's training-iteration boundary, after which the driver independently recomputes
        the winner, verifies every worker reported the same winner/checkpoint source, captures
        that source once, pauses all members without duplicate saves, and installs every child
        continuation before clearing the scheduling gate.

        The deliberate worker/driver redundancy detects mismatched validation state, rank
        identity, or selection behavior before CBT propagates the wrong checkpoint.
        """

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

        mode = self._mode
        if mode is None:
            raise RuntimeError("Tune did not configure the Clan selection mode")

        ordered_trials = self._ordered_trials(tune_controller)
        ordered_reports = [self._reports[candidate.trial_id] for candidate in ordered_trials]
        decision = self._generation_resolver(
            fitnesses=[float(report[self.metric]) for report in ordered_reports],
            configs=[candidate.config for candidate in ordered_trials],
            mode=mode,
            mutations=self._mutations,
            random_stream=self._random,
        )
        self._validate_worker_decision(ordered_reports, decision.winner_id)

        winner_trial = ordered_trials[decision.winner_id]
        winner_report = ordered_reports[decision.winner_id]
        checkpoint = self._checkpoint_capture(tune_controller, winner_trial, winner_report)

        # The callback may still be executing inside one running trial. Pause every member
        # without another checkpoint request, then install one explicit parent continuation
        # everywhere before Tune is allowed to schedule any child.
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
        """Release scheduler-owned runtime state only after the full successful Clan exits.

        The shared registry/coordinator must outlive individual members because other members
        may still be running. Error paths intentionally do not use this cleanup hook; retaining
        the assignment lets Ray's retry/restore policy decide whether the experiment resumes.
        """

        super().on_trial_complete(tune_controller, trial, result)
        if trial.trial_id not in self._trial_ids:
            return

        self._finished_trial_ids.add(trial.trial_id)
        if self._finished_trial_ids == self._trial_ids:
            self._release_runtime()

    def debug_string(self) -> str:
        """Provide Tune's scheduler-status hook without exposing internal state as an API."""

        return "Using Clan synchronous single-parent scheduling."

    def _validate_report_identity(self, trial: Trial, result: dict[str, Any]) -> None:
        """Cross-check worker DDP rank identity against the driver's stable trial mapping.

        Member ID appears in the Tune result specifically so this check can detect a worker
        that joined the wrong cohort/rank before its fitness participates in parent selection.
        """

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
        """Treat worker/driver agreement as a distributed-state integrity check.

        Every worker sees the gathered fitness vector and independently resolves a winner so
        only that rank writes the Lightning checkpoint. The driver resolves the same decision
        from Tune results. A mismatch is therefore not cosmetic: continuing would risk pairing
        one member's checkpoint with another member's selected config.
        """

        for member_id, report in enumerate(ordered_reports):
            if int(report[CLAN_WINNER_ID]) != winner_id:
                raise RuntimeError("worker and scheduler winner selection disagree")
            expected_checkpoint_source = member_id == winner_id
            if bool(report[CLAN_CHECKPOINT_SOURCE]) != expected_checkpoint_source:
                raise RuntimeError("Clan result reports the wrong checkpoint source")

    def _ordered_trial_ids(self) -> list[str]:
        """Recover the canonical member order established when the population was frozen.

        Do not replace this with Tune controller iteration order: this order controls DDP rank
        identity and which seeded mutation is assigned to each stable member.
        """

        return [
            trial_id
            for trial_id, _member_id in sorted(
                self._member_ids.items(),
                key=lambda item: item[1],
            )
        ]

    def _ordered_trials(self, tune_controller: Any) -> list[Trial]:
        """Map Tune's live trial objects back onto canonical Clan member order.

        Missing registered members are treated as corruption rather than silently shrinking
        the generation, because CBT's gradient-sharing and single-parent semantics require the
        complete population at every boundary.
        """

        by_id = {
            candidate.trial_id: candidate
            for candidate in tune_controller.get_trials()
            if candidate.trial_id in self._member_ids
        }
        if set(by_id) != set(self._member_ids):
            raise RuntimeError("Tune controller does not contain the complete registered Clan")
        return [by_id[trial_id] for trial_id in self._ordered_trial_ids()]

    def _register_runtime(self) -> None:
        """Ensure worker discovery state exists once per live scheduler process.

        Actor handles are deliberately absent after scheduler deserialization, so the same
        operation also reconstructs runtime discovery after ``Tuner.restore``. The boolean
        prevents ordinary scheduling callbacks from paying repeated synchronous registration
        RPCs once the assignment is live.
        """

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
        """Remove successful-run discovery state without disturbing unrelated experiments.

        The registry is cluster-wide, so cleanup removes only this experiment's trial keys;
        the coordinator actor is scheduler-owned and may be terminated entirely.
        """

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
        """Serialize durable scheduler authority while discarding process-local Ray handles.

        Tune restores the scheduler in a new Ray runtime where old actor handles are invalid.
        Keeping member IDs, reports, RNG state, and runtime specification preserves algorithmic
        authority; clearing only live handles lets ``_register_runtime`` rebuild discovery.
        """

        state = self.__dict__.copy()
        state["_coordinator_handle"] = None
        state["_registry_handle"] = None
        state["_runtime_registered"] = False
        return state
