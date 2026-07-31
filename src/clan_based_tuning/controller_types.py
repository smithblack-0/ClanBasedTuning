"""Framework-independent primitives shared by CBT workers and the Tune scheduler."""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MutationSpec:
    """Apply one bounded mutation rule to a named scalar value."""

    standard_deviation: float
    geometry: str
    minimum: float
    maximum: float

    def mutate(self, value, random_stream):
        """Return one bounded mutation of ``value``."""

        displacement = random_stream.gauss(0.0, self.standard_deviation)
        if self.geometry == "linear":
            candidate = value + displacement
        elif self.geometry == "log":
            candidate = value * math.exp(displacement)
        else:
            raise ValueError(f"unknown mutation geometry: {self.geometry}")
        return min(max(candidate, self.minimum), self.maximum)


def select_winner_id(population, mode):
    """Return one stable winner from rank-ordered fitness values."""

    ranked = enumerate(population)
    if mode == "min":
        return min(ranked, key=lambda item: (item[1], item[0]))[0]
    if mode == "max":
        return max(ranked, key=lambda item: (item[1], -item[0]))[0]
    raise ValueError("mode must be 'min' or 'max'")


def build_parent_genome_metadata(
    *,
    round_index,
    source_member_id,
    source_trial_id,
    genome,
):
    """Return checkpoint metadata binding a continuation to its parent genome.

    The scheduler supplies only the controlled genome subset, not the complete Tune
    configuration. Ray can merge this namespaced mapping into checkpoint metadata
    without loading the Lightning checkpoint payload.
    """

    return {
        "clan_based_tuning": {
            "schema_version": 1,
            "round_index": round_index,
            "source_member_id": source_member_id,
            "source_trial_id": source_trial_id,
            "parent_genome": dict(genome),
        }
    }


def attach_parent_genome_metadata(
    checkpoint,
    *,
    round_index,
    source_member_id,
    source_trial_id,
    genome,
):
    """Attach scheduler-owned parent provenance to a Ray checkpoint sidecar."""

    checkpoint.update_metadata(
        build_parent_genome_metadata(
            round_index=round_index,
            source_member_id=source_member_id,
            source_trial_id=source_trial_id,
            genome=genome,
        )
    )
    return checkpoint
