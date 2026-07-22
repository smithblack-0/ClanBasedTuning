"""Lightning cluster environment for one native Tune trial in a clan."""

from __future__ import annotations

from dataclasses import dataclass

from lightning.pytorch.plugins.environments import ClusterEnvironment


@dataclass(frozen=True, slots=True)
class ClanRuntime:
    """Resolved process-group identity for one running Tune trial actor."""

    trial_id: str
    actor_token: str
    session_id: int
    global_rank: int
    world_size: int
    master_address: str
    master_port: int
    checkpoint_available: bool = False

    def __post_init__(self) -> None:
        if not self.trial_id:
            raise ValueError("trial_id must be non-empty")
        if not self.actor_token:
            raise ValueError("actor_token must be non-empty")
        if self.session_id < 0:
            raise ValueError("session_id must be non-negative")
        if not 0 <= self.global_rank < self.world_size:
            raise ValueError("global_rank must be within world_size")
        if self.world_size < 2:
            raise ValueError("world_size must be at least 2")
        if not self.master_address:
            raise ValueError("master_address must be non-empty")
        if not 0 < self.master_port < 65536:
            raise ValueError("master_port must be a valid TCP port")


class ClanClusterEnvironment(ClusterEnvironment):
    """Expose an externally launched cross-trial process group to Lightning.

    Lightning must not launch subprocesses or overwrite ranks. Each native Tune
    trial already owns one process and receives its rank from the clan
    rendezvous.
    """

    def __init__(self, runtime: ClanRuntime) -> None:
        super().__init__()
        self._runtime = runtime

    @property
    def creates_processes_externally(self) -> bool:
        return True

    @property
    def main_address(self) -> str:
        return self._runtime.master_address

    @property
    def main_port(self) -> int:
        return self._runtime.master_port

    @staticmethod
    def detect() -> bool:
        return False

    def world_size(self) -> int:
        return self._runtime.world_size

    def set_world_size(self, size: int) -> None:
        del size

    def global_rank(self) -> int:
        return self._runtime.global_rank

    def set_global_rank(self, rank: int) -> None:
        del rank

    def local_rank(self) -> int:
        return 0

    def node_rank(self) -> int:
        # Each Trainer owns one process and does not launch a multi-node job.
        # Global rank comes directly from the external clan runtime.
        return 0

    def teardown(self) -> None:
        return None
