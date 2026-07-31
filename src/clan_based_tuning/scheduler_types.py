"""Dictionary aliases for scheduler-owned Clan Tuning state."""

from typing import TypeAlias

Genome: TypeAlias = dict[str, object]
PopulationGenomes: TypeAlias = dict[int, Genome]
