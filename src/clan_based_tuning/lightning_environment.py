"""Lightning cluster environment for one externally launched Tune member process.

Ray launches one process and exposes one device per Clan member. Lightning still expects a
``ClusterEnvironment`` describing ranks and rendezvous facts before it initializes PyTorch
DDP. ``TuneMemberEnvironment`` supplies those immutable facts without owning process launch,
backend selection, process-group creation, collectives, or teardown.

Each Tune member is represented as one logical one-process Lightning node: ``local_rank`` is
zero while ``node_rank`` and ``global_rank`` both identify the stable Clan member. This is a
framework adapter representation, not a claim that every member runs on a distinct physical
machine.
"""

from lightning.pytorch.plugins.environments import ClusterEnvironment

from clan_based_tuning.cohort import ClanRuntime


class TuneMemberEnvironment(ClusterEnvironment):
    """Expose scheduler-assigned one-process-per-member topology to Lightning."""

    def __init__(
        self,
        *,
        global_rank: int,
        world_size: int,
        local_rank: int,
        node_rank: int,
        main_address: str,
        main_port: int,
    ) -> None:
        if world_size < 2:
            raise ValueError("world_size must contain at least two Clan members")
        if not 0 <= global_rank < world_size:
            raise ValueError("global_rank must identify one member of the distributed world")

        self._global_rank = global_rank
        self._world_size = world_size
        self._local_rank = local_rank
        self._node_rank = node_rank
        self._main_address = main_address
        self._main_port = main_port

    @property
    def creates_processes_externally(self) -> bool:
        """Tell Lightning that Ray Tune already launched every member process."""

        return True

    @property
    def main_address(self) -> str:
        """Return the scheduler-supplied rendezvous address."""

        return self._main_address

    @property
    def main_port(self) -> int:
        """Return the scheduler-supplied rendezvous port."""

        return self._main_port

    @staticmethod
    def detect() -> bool:
        """Require explicit construction because arbitrary Tune trials are not a Clan."""

        return False

    def world_size(self) -> int:
        """Return the complete externally assigned Clan world size."""

        return self._world_size

    def set_world_size(self, size: int) -> None:
        """Reject a Lightning configuration that conflicts with scheduler topology."""

        if size != self._world_size:
            raise RuntimeError("Lightning world size conflicts with the assigned Clan topology")

    def global_rank(self) -> int:
        """Return this member process's externally assigned distributed rank."""

        return self._global_rank

    def set_global_rank(self, rank: int) -> None:
        """Reject a Lightning configuration that changes the assigned member rank."""

        if rank != self._global_rank:
            raise RuntimeError("Lightning global rank conflicts with the assigned Clan topology")

    def local_rank(self) -> int:
        """Return zero for the single process/device visible inside this Tune trial."""

        return self._local_rank

    def node_rank(self) -> int:
        """Return the logical one-process-node index used to preserve the external rank."""

        return self._node_rank


def build_tune_member_environment(
    runtime: ClanRuntime,
    _cls: type[TuneMemberEnvironment] = TuneMemberEnvironment,
) -> TuneMemberEnvironment:
    """Construct Lightning's topology adapter from one resolved Clan runtime."""

    return _cls(
        global_rank=runtime.member_id,
        world_size=runtime.world_size,
        local_rank=0,
        node_rank=runtime.member_id,
        main_address=runtime.main_address,
        main_port=runtime.main_port,
    )
