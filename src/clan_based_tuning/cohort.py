"""Pure cohort identity and rendezvous state for Clan Tune members.

The Ray runtime adapter places these objects inside named actors, but the state machine itself
has no Ray, socket, or process-group effects. ``RuntimeRegistry`` answers "which Clan owns this
experiment/trial?" while ``ClanCoordinator`` answers "which stable member is this trial, and
are all members from the same function invocation ready to enter DDP?" Keeping those questions
pure makes the failure/rendezvous invariants testable without a distributed runtime.
"""

from dataclasses import dataclass

# Helpers


@dataclass(frozen=True, slots=True)
class _PendingMember:
    """One not-yet-complete invocation announcement.

    ``token`` distinguishes process invocations of the same stable Tune trial. Only rank zero
    contributes the DDP rendezvous endpoint; other members need only prove readiness with a
    fresh token.
    """

    token: str
    main_address: str | None
    main_port: int | None


@dataclass(frozen=True, slots=True)
class _Session:
    """Immutable rendezvous snapshot shared by one complete invocation cohort.

    The per-trial token map is the session identity: it prevents a process from reading a
    rendezvous opened for an older invocation of the same Tune trial. No separate session
    counter is required.
    """

    tokens: dict[str, str]
    main_address: str
    main_port: int


# Main


@dataclass(frozen=True, slots=True)
class ClanRuntimeSpec:
    """Scheduler authority that every member needs before it can join the Clan.

    ``coordinator_name`` identifies this scheduler instance. ``experiment_name`` scopes trial
    IDs in the cluster-wide registry so independent Tune runs cannot collide. The selection
    and timeout fields are immutable because workers and driver must make the same decision
    and observe the same rendezvous policy across retries/restores.
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
    """Resolved process-local identity needed to hand this Tune trial to Lightning.

    ``member_id`` is both the stable Clan member identity and externally assigned DDP global
    rank. ``main_address``/``main_port`` identify the rank-zero rendezvous selected for this
    exact function invocation.
    """

    spec: ClanRuntimeSpec
    trial_id: str
    member_id: int
    main_address: str
    main_port: int


class RuntimeRegistry:
    """Cluster-wide lookup from experiment-scoped Tune trials to scheduler authority.

    Ray wraps one instance as a named actor. The small RPC-shaped methods are intentional:
    member processes may start independently from the driver and must discover their runtime
    assignment without receiving CBT state through the user's Tune config.
    """

    def __init__(self) -> None:
        self._runtime_specs: dict[tuple[str, str], ClanRuntimeSpec] = {}

    def register_trials(
        self,
        experiment_name: str,
        trial_ids: list[str],
        runtime_spec: ClanRuntimeSpec,
    ) -> None:
        """Install one assignment idempotently, rejecting identity reuse by another Clan.

        Re-registration is expected after scheduler restore, so writing the same mapping again
        is harmless. A different spec for an existing experiment/trial key is rejected because
        silently redirecting a live/restored worker would join it to the wrong DDP world.
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
        """Remove only this experiment's completed assignments from the shared registry.

        Missing keys are tolerated because successful cleanup is idempotent; unrelated
        experiments sharing the registry remain untouched.
        """

        for trial_id in trial_ids:
            self._runtime_specs.pop((experiment_name, trial_id), None)

    def get_runtime_spec(self, experiment_name: str, trial_id: str) -> ClanRuntimeSpec | None:
        """Support worker polling while scheduler registration races process startup.

        ``None`` means "not registered yet", not "invalid trial"; ``join_runtime`` bounds that
        polling with its bootstrap timeout.
        """

        return self._runtime_specs.get((experiment_name, trial_id))


class ClanCoordinator:
    """Bind stable members and same-invocation processes into one rendezvous session.

    Trial registration is immutable once established and defines stable member IDs by sorted
    trial ID. Every subsequent function invocation announces a fresh token. A session opens
    only when every registered member has a pending token, preventing an early restarted
    member from entering DDP with peers still executing the previous invocation.

    A process that abandons pre-DDP rendezvous can retract only its exact token. This prevents
    both stale dead-peer sessions and an older failing process from deleting a newer retry's
    announcement.
    """

    def __init__(self, population_size: int) -> None:
        self.population_size = population_size
        self.member_ids: dict[str, int] = {}
        self._pending: dict[str, _PendingMember] = {}
        self._last_tokens: dict[str, str] = {}
        self._session: _Session | None = None

    def validate_population_size(self, population_size: int) -> None:
        """Protect named-actor reuse from binding a new scheduler to an old cohort shape.

        ``get_if_exists=True`` may return a pre-existing actor after restore. The actor is safe
        to reuse only when its immutable population size matches the restoring scheduler.
        """

        if population_size != self.population_size:
            raise RuntimeError("existing Clan coordinator has a different population size")

    def register_trials(self, trial_ids: list[str]) -> None:
        """Freeze the complete Tune population into deterministic stable member IDs.

        Sorting makes member/rank identity independent of Tune's trial-creation order. Once a
        coordinator has an assignment, a different population is rejected rather than
        remapping ranks underneath live or restored workers.
        """

        if len(trial_ids) != self.population_size:
            raise ValueError("Clan coordinator requires the complete Tune population")
        if len(set(trial_ids)) != len(trial_ids):
            raise ValueError("Tune trial IDs must be unique")

        assignment = {trial_id: member_id for member_id, trial_id in enumerate(sorted(trial_ids))}
        if self.member_ids and self.member_ids != assignment:
            raise RuntimeError("Clan coordinator was already registered with another population")
        self.member_ids = assignment

    def get_member_id(self, trial_id: str) -> int | None:
        """Let workers poll until registration has assigned their stable DDP rank.

        ``None`` is transient during startup; an unknown trial becomes a bounded runtime
        failure in ``join_runtime`` rather than an actor-side exception that obscures context.
        """

        return self.member_ids.get(trial_id)

    def announce(
        self,
        trial_id: str,
        token: str,
        main_address: str | None,
        main_port: int | None,
    ) -> None:
        """Publish readiness for one exact function invocation and try to open its session.

        Rank zero alone supplies the rendezvous address/port because every member must converge
        on one endpoint. Other members publish no unused network identity. Reusing the previous
        completed token is rejected: without fresh invocation identity, a restarted process
        could consume a session belonging to its predecessor.
        """

        if trial_id not in self.member_ids:
            raise RuntimeError(f"Tune trial {trial_id!r} is not registered with this Clan")
        member_id = self.member_ids[trial_id]
        if not token:
            raise ValueError("runtime token must be non-empty")
        if member_id == 0 and (not main_address or main_port is None):
            raise ValueError("member zero must provide the DDP rendezvous address and port")
        if member_id != 0 and (main_address is not None or main_port is not None):
            raise ValueError("only member zero may provide the DDP rendezvous endpoint")
        if self._last_tokens.get(trial_id) == token:
            raise RuntimeError("a function invocation cannot reuse its previous runtime token")

        self._pending[trial_id] = _PendingMember(
            token=token,
            main_address=main_address,
            main_port=main_port,
        )
        self._try_open_session()

    def abort_announcement(self, trial_id: str, token: str) -> None:
        """Retract only the failed process's still-current pre-DDP announcement.

        A stale/superseded token is intentionally ignored. That compare-before-delete is what
        makes timeout cleanup safe when Ray has already started a newer invocation of the same
        stable trial.
        """

        if trial_id not in self.member_ids:
            raise RuntimeError(f"Tune trial {trial_id!r} is not registered with this Clan")
        pending = self._pending.get(trial_id)
        if pending is not None and pending.token == token:
            del self._pending[trial_id]

    def get_session(self, trial_id: str, token: str) -> dict[str, int | str] | None:
        """Expose a session only to the exact invocation that participated in opening it.

        The coordinator retains the completed session long enough for independently polling
        members to read it. Token matching prevents a later retry of the same trial from
        inheriting that stale endpoint while another generation is forming.
        """

        session = self._session
        if session is None or session.tokens.get(trial_id) != token:
            return None
        return {
            "member_id": self.member_ids[trial_id],
            "main_address": session.main_address,
            "main_port": session.main_port,
        }

    def _try_open_session(self) -> None:
        """Atomically snapshot a complete pending cohort into one immutable DDP session.

        The pending set must exactly equal the registered population. Rank zero's announced
        address/port becomes the common rendezvous endpoint. Once snapshotted, pending entries
        are cleared so announcements for the next invocation cannot mix with the current
        session; ``_last_tokens`` separately prevents completed-token reuse.
        """

        if len(self.member_ids) != self.population_size:
            return
        if set(self._pending) != set(self.member_ids):
            return

        rank_zero_trial = next(
            trial_id for trial_id, member_id in self.member_ids.items() if member_id == 0
        )
        rank_zero = self._pending[rank_zero_trial]
        if rank_zero.main_address is None or rank_zero.main_port is None:
            raise RuntimeError("rank-zero rendezvous endpoint disappeared before session creation")

        tokens = {trial_id: member.token for trial_id, member in self._pending.items()}
        self._session = _Session(
            tokens=tokens,
            main_address=rank_zero.main_address,
            main_port=rank_zero.main_port,
        )
        self._last_tokens = tokens
        self._pending = {}
