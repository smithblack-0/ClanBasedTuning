# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient
training with member-local optimizer hyperparameters and population selection.

## Current implementation surface

The active implementation contains the first framework-independent pieces required by
the accepted Tune-shaped design:

- `ClanController` is a thin worker-side collective manager. It stores one local
  fitness value and answers whether that Tune worker should attach the generation
  checkpoint.
- `MutationSpec` defines one bounded mutation rule for the future CBT Tune scheduler.
- worker and scheduler code share one stable winner-selection implementation; and
- the core still contains an older parent-genome metadata builder that is scheduled for
  replacement.

The corrected Milestone 3 controller design additionally requires:

- construction with an immutable copy of the current scheduler-assigned genome; and
- winner-only `save_genome(checkpoint)` before the checkpoint is reported to Tune.

The selected worker will write only:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

The worker controller does not advance generations, mutate genomes, retain scheduler
state, serialize a continuation of itself, or construct another round.

The CBT Tune scheduler remains the evolutionary authority. It decides population
genomes, materializes the current assignment in each member's `Trial.config`, verifies
the winning checkpoint's producer metadata, derives child genomes, persists mutation
and replay lineage, and assigns the selected training checkpoint to every next member.

The controller's genome copy and the checkpoint metadata are provenance, not a second
genome authority.

The active module layout is transitional: mutation and shared selection concerns must
move out of `controller_types.py` as the corrected controller API is implemented.

Ray collective construction, Lightning DDP integration, winner-aware checkpoint
persistence, the CBT Tune scheduler, and the public
`make_cbt_controller(genome=...)` factory are not yet active package surfaces.
Historical proof-of-concept implementations remain available only through git history
and are described in [`old_code/README.md`](old_code/README.md).

Read [`STATUS.md`](STATUS.md) for the current durable project position.

## Documentation

- [`docs/product_roadmap.md`](docs/product_roadmap.md) — governing product meaning,
  development criteria, and milestone sequence.
- [`docs/decisions/project_decisions.md`](docs/decisions/project_decisions.md) —
  accepted cross-milestone technical decisions.
- [`docs/milestones/README.md`](docs/milestones/README.md) — milestone-gate rules.
- [`docs/design/README.md`](docs/design/README.md) — accepted Milestone 3 system flow.
- [`docs/controller/README.md`](docs/controller/README.md) — worker controller lifecycle,
  ownership, and intended API.
- [`docs/framework_alignment/README.md`](docs/framework_alignment/README.md) —
  accepted framework research and responsibility model.
- [`AGENTS.md`](AGENTS.md) — contributor and coding-agent entry point.

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
