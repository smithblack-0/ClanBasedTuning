"""Pure cohort identity and rendezvous state for Clan Tune members.

The Ray runtime adapter creates these objects inside named actors, but their behavior is
framework-independent. ``RuntimeRegistry`` maps one experiment/trial identity to a Clan
runtime specification. ``ClanCoordinator`` assigns stable member IDs and opens one rendezvous
session only after every registered member announces the same function invocation boundary.
No object here creates actors, touches sockets, or initializes distributed process groups.
"""

from dataclasses import dataclass

# Helpers


@dataclass(frozen=True, slots=True)
class _PendingMember:
    """One member announcement waiting for the complete invocation cohort."""

    token: str
    host: str
    port: int | None


@dataclass(frozen=True, slots=True)
class _Session:
    """One complete invocation cohort sharing a single DDP rendezvous endpoint."""

    session_id: int
    tokens: dict[str, str]
    main_address: str
    main_port: int


# Main


@dataclass(frozen=True, slots=True)
class ClanRuntimeSpec:
    """Scheduler-owned configuration needed for one Clan cohort.

    ``coordinator_name`` uniquely identifies this scheduler instance. ``experiment_name`` is
    paired with Tune trial IDs so concurrently running experiments cannot collide in the
    process-wide registry. The remaining values are immutable facts consumed by every member
    while it discovers and joins the cohort.
    """

    coordinator_name: str
    experiment_name: str
    population_size: int
    metric: str
    mode: str
    join_timeout_s: float
    poll_interval_s: float
    namespace: str


@dataclass(frozen=True, slots=True)
class ClanRuntime:
    """Process-local member identity and externally assigned DDP rendezvous facts."""

    spec: ClanRuntimeSpec
    trial_id: str
    member_id: int
    main_address: str
    main_port: int

    @property
    def world_size(self) -> int:
        """Return the complete Clan member count used as the DDP world size."""

        return self.spec.population_size


class RuntimeRegistry:
    """Keep experiment-scoped trial assignments discoverable by Tune member processes.

    One cluster-local Ray actor wraps this pure state. Schedulers add assignments before
    members launch and remove them after the complete successful population finishes. Lookup
    keys include both experiment and trial identity so unrelated Tune runs cannot collide.
    """

    def __init__(self) -> None:
        self._runtime_specs: dict[tuple[str, str], ClanRuntimeSpec] = {}

    def register_trials(
        self,
        experiment_name: str,
        trial_ids: list[str],
        runtime_spec: ClanRuntimeSpec,
    ) -> None:
        """Register one complete scheduler assignment idempotently.

        A conflicting assignment for the same experiment/trial identity is rejected rather
        than silently redirecting a live or restored member into another Clan.
        """

        for trial_id in trial_ids:
            key = (experiment_name, trial_id)
            existing = self._runtime_specs.get(key)
            if existing is not None and existing != runtime_spec:
                raise RuntimeError(
                    f"Tune trial {trial_id!r} is already registered with another Clan runtime"
                )
        for trial_id in trial_ids:
            self._runtime_specs[(experiment_name, trial_id)] = runtime_spec

    def unregister_trials(self, experiment_name: str, trial_ids: list[str]) -> None:
        """Remove completed assignments without affecting other experiments or trials."""

        for trial_id in trial_ids:
            self._runtime_specs.pop((experiment_name, trial_id), None)

    def get_runtime_spec(self, experiment_name: str, trial_id: str) -> ClanRuntimeSpec | None:
        """Return the assignment for one experiment-scoped trial, if registered."""

        return self._runtime_specs.get((experiment_name, trial_id))


class ClanCoordinator:
    """Hold stable member assignment and per-invocation rendezvous state only.

    Trial registration fixes the mapping from Tune trial ID to Clan member ID. Each function
    invocation supplies a fresh token; a session opens only when every member has announced,
    preventing members from different invocations from entering one DDP rendezvous. A member
    that abandons a pre-DDP rendezvous retracts its token so a later process cannot form a
    session with a dead participant.
    """

    def __init__(self, population_size: int) -> None:
        self.population_size = population_size
        self.member_ids: dict[str, int] = {}
        self._pending: dict[str, _PendingMember] = {}
        self._last_tokens: dict[str, str] = {}
        self._session: _Session | None = None
        self._next_session_id = 0

    def validate_population_size(self, population_size: int) -> None:
        """Reject reuse of a named coordinator for a different Clan size."""

        if population_size != self.population_size:
            raise RuntimeError("existing Clan coordinator has a different population size")

    def register_trials(self, trial_ids: list[str]) -> None:
        """Fix stable member IDs for exactly one complete Tune population."""

        if len(trial_ids) != self.population_size:
            raise ValueError("Clan coordinator requires the complete Tune population")
        if len(set(trial_ids)) != len(trial_ids):
            raise ValueError("Tune trial IDs must be unique")

        assignment = {trial_id: member_id for member_id, trial_id in enumerate(sorted(trial_ids))}
        if self.member_ids and self.member_ids != assignment:
            raise RuntimeError("Clan coordinator was already registered with another population")
        self.member_ids = assignment

    def get_member_id(self, trial_id: str) -> int | None:
        """Return the stable member ID assigned to ``trial_id``."""

        return self.member_ids.get(trial_id)

    def announce(self, trial_id: str, token: str, host: str, port: int | None) -> None:
        """Record one member's readiness for its current function invocation."""

        member_id = self._require_member(trial_id)
        if not token:
            raise ValueError("runtime token must be non-empty")
        if not host:
            raise ValueError("runtime host must be non-empty")
        if member_id == 0 and port is None:
            raise ValueError("member zero must provide the DDP rendezvous port")
        if member_id != 0 and port is not None:
            raise ValueError("only member zero may provide the DDP rendezvous port")
        if self._last_tokens.get(trial_id) == token:
            raise RuntimeError("a function invocation cannot reuse its previous runtime token")

        self._pending[trial_id] = _PendingMember(token=token, host=host, port=port)
        self._try_open_session()

    def abort_announcement(self, trial_id: str, token: str) -> None:
        """Retract this exact pending invocation announcement after pre-DDP failure.

        A stale or superseded token is ignored so an older failing process cannot remove a
        newer invocation that has already replaced its pending announcement.
        """

        self._require_member(trial_id)
        pending = self._pending.get(trial_id)
        if pending is not None and pending.token == token:
            del self._pending[trial_id]

    def get_session(self, trial_id: str, token: str) -> dict[str, int | str] | None:
        """Return the opened session only when it contains this trial's current token."""

        session = self._session
        if session is None or session.tokens.get(trial_id) != token:
            return None
        return {
            "session_id": session.session_id,
            "member_id": self.member_ids[trial_id],
            "main_address": session.main_address,
            "main_port": session.main_port,
        }

    def _require_member(self, trial_id: str) -> int:
        """Return the stable member ID or reject an unregistered Tune trial."""

        member_id = self.member_ids.get(trial_id)
        if member_id is None:
            raise RuntimeError(f"Tune trial {trial_id!r} is not registered with this Clan")
        return member_id

    def _try_open_session(self) -> None:
        """Open one rendezvous session only after every registered member has announced."""

        if len(self.member_ids) != self.population_size:
            return
        if set(self._pending) != set(self.member_ids):
            return

        rank_zero_trial = next(
            trial_id for trial_id, member_id in self.member_ids.items() if member_id == 0
        )
        rank_zero = self._pending[rank_zero_trial]
        if rank_zero.port is None:
            raise RuntimeError("rank-zero rendezvous port disappeared before session creation")

        tokens = {trial_id: member.token for trial_id, member in self._pending.items()}
        self._session = _Session(
            session_id=self._next_session_id,
            tokens=tokens,
            main_address=rank_zero.host,
            main_port=rank_zero.port,
        )
        self._next_session_id += 1
        self._last_tokens = tokens
        self._pending = {}
