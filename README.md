# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient
training with member-local optimizer hyperparameters and population selection.

## Current implementation surface

The active implementation now contains two framework-independent pieces required by
the accepted Tune-shaped design:

- `ClanController` is a thin worker-side collective manager. It stores one local
  fitness value and answers whether that Tune worker should attach the round
  checkpoint.
- `MutationSpec` defines one bounded mutation rule for the future CBT Tune scheduler.

The worker controller does not advance generations, own mutation state, serialize into
training checkpoints, or construct another round. The Tune scheduler will own parent
selection, mutation, trial configuration, replay state, and winner-checkpoint
assignment.

Ray collective construction, Lightning DDP integration, winner-aware checkpoint
persistence, the CBT Tune scheduler, and the public `make_cbt_controller()` factory are
not yet active package surfaces. Historical proof-of-concept implementations remain
available only through git history and are described in
[`old_code/README.md`](old_code/README.md).

Read [`STATUS.md`](STATUS.md) for the current durable project position.

## Documentation

- [`docs/product_roadmap.md`](docs/product_roadmap.md) — governing product meaning,
  development criteria, and milestone sequence.
- [`docs/decisions/project_decisions.md`](docs/decisions/project_decisions.md) —
  accepted cross-milestone technical decisions.
- [`docs/milestones/README.md`](docs/milestones/README.md) — milestone-gate rules.
- [`docs/design/README.md`](docs/design/README.md) — accepted Milestone 3 system flow.
- [`docs/controller/README.md`](docs/controller/README.md) — worker controller lifecycle,
  ownership, and API reference.
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
