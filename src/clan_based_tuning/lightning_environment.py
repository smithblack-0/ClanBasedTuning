"""Lightning cluster environment for one externally launched Tune member."""

from lightning.pytorch.plugins.environments import ClusterEnvironment


class TuneMemberEnvironment(ClusterEnvironment):
    """Expose scheduler-assigned topology without owning distributed lifecycle.

    Ray Tune launches and resources the current process. This environment reports the
    immutable rank, world-size, and rendezvous facts assigned to that process so
    Lightning and PyTorch can establish and use their native distributed context. The
    surrounding framework process lifecycle remains responsible for releasing it. This
    environment never initializes, destroys, or selects a process-group backend.
    """

    def __init__(
        self,
        *,
        global_rank: int,
        world_size: int,
        local_rank: int,
        node_rank: int,
        main_address: str,
        main_port: int,
    ):
        if world_size < 2:
            raise ValueError("world_size must contain at least two Clan members")
        if not 0 <= global_rank < world_size:
            raise ValueError("global_rank must identify one member of the distributed world")
        if local_rank < 0:
            raise ValueError("local_rank must be non-negative")
        if node_rank < 0:
            raise ValueError("node_rank must be non-negative")
        if not main_address:
            raise ValueError("main_address must be non-empty")
        if not 1 <= main_port <= 65_535:
            raise ValueError("main_port must be a valid TCP port")

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
        """Return the process-local rank for the framework-assigned visible device."""

        return self._local_rank

    def node_rank(self) -> int:
        """Return the logical Lightning node rank assigned to this external process."""

        return self._node_rank
