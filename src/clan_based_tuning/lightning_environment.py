"""Lightning cluster environment for one externally launched Tune member process.

Ray launches one process/device per Clan member, while Lightning expects one
``ClusterEnvironment`` to describe the ranks and rendezvous endpoint before DDP setup. This
adapter supplies only those facts. It does not launch processes, choose the backend, create the
process group, or own collectives/teardown.

The unusual part is deliberate: every Tune trial is a separate OS process with local rank 0,
but CBT presents each process as a logical one-process Lightning node. Therefore node rank and
global rank are the same stable Clan member ID. This is framework bookkeeping, not a claim
that each member runs on a different physical host.
"""

from lightning.pytorch.plugins.environments import ClusterEnvironment

from clan_based_tuning.cohort import ClanRuntime

# Main


class TuneMemberEnvironment(ClusterEnvironment):
    """Present one already-running Tune member as a fixed external Lightning rank.

    Only values that can legitimately vary are constructor inputs. ``local_rank`` is always
    zero and ``node_rank`` always equals ``global_rank`` for the supported one-process-per-
    trial topology, so callers cannot construct a contradictory mapping.

    Lightning may call the setter methods during strategy setup. They are validation hooks,
    not mutation hooks: CBT's scheduler/runtime already assigned the world before Lightning
    entered it, so a different value indicates framework configuration drift and is rejected.
    """

    def __init__(
        self,
        *,
        global_rank: int,
        world_size: int,
        main_address: str,
        main_port: int,
    ) -> None:
        if world_size < 2:
            raise ValueError("world_size must contain at least two Clan members")
        if not 0 <= global_rank < world_size:
            raise ValueError("global_rank must identify one member of the distributed world")

        self._global_rank = global_rank
        self._world_size = world_size
        self._main_address = main_address
        self._main_port = main_port

    @property
    def creates_processes_externally(self) -> bool:
        """Prevent Lightning from spawning processes that Ray Tune already launched."""

        return True

    @property
    def main_address(self) -> str:
        """Give every rank the rank-zero rendezvous host selected for this invocation."""

        return self._main_address

    @property
    def main_port(self) -> int:
        """Give every rank the rank-zero rendezvous port selected for this invocation."""

        return self._main_port

    @staticmethod
    def detect() -> bool:
        """Disable automatic detection because an arbitrary Tune trial is not necessarily CBT.

        The strategy constructs this environment only after successful Clan runtime discovery;
        environment-variable heuristics would risk attaching CBT topology to unrelated Tune
        workloads.
        """

        return False

    def world_size(self) -> int:
        """Expose the immutable scheduler-assigned Clan population as Lightning's DDP world."""

        return self._world_size

    def set_world_size(self, size: int) -> None:
        """Catch Lightning configuration that would split or enlarge the fixed Clan world."""

        if size != self._world_size:
            raise RuntimeError("Lightning world size conflicts with the assigned Clan topology")

    def global_rank(self) -> int:
        """Expose the stable Clan member ID as the process's DDP global rank."""

        return self._global_rank

    def set_global_rank(self, rank: int) -> None:
        """Reject any attempt to remap the stable member after runtime rendezvous."""

        if rank != self._global_rank:
            raise RuntimeError("Lightning global rank conflicts with the assigned Clan topology")

    def local_rank(self) -> int:
        """Report local rank zero because each Tune trial exposes exactly one process/device."""

        return 0

    def node_rank(self) -> int:
        """Use the member ID as a logical one-process-node rank for Lightning's rank formula.

        ``ClanDDPStrategy.set_world_ranks`` preserves the externally assigned global rank, so
        this value is topology metadata for Lightning rather than physical-node identity.
        """

        return self._global_rank


# Construction


def build_tune_member_environment(
    runtime: ClanRuntime,
    _cls: type[TuneMemberEnvironment] = TuneMemberEnvironment,
) -> TuneMemberEnvironment:
    """Translate resolved Clan runtime identity into Lightning topology exactly once.

    Keeping this translation outside ``ClanDDPStrategy`` prevents the strategy from learning
    Ray runtime layout and gives tests one construction seam. A replacement class must honor
    the same fixed mapping: member ID -> global/node rank, with one local process per trial.
    """

    return _cls(
        global_rank=runtime.member_id,
        world_size=runtime.spec.population_size,
        main_address=runtime.main_address,
        main_port=runtime.main_port,
    )
