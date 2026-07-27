# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient
training with member-local optimizer hyperparameters and population selection.

## Current implementation surface

The active implementation is intentionally limited to the accepted Milestone 2
framework-independent evolutionary subsystem:

- `MutationSpec` defines one bounded mutation rule.
- `ClanRound` carries one member's optimizer configuration and fitness.
- `ClanController` advances one member through the accepted population-policy lifecycle.

Ray Tune, Lightning, DDP setup, checkpoint integration, optimizer application, and
end-to-end training orchestration are not active package surfaces. Earlier
proof-of-concept implementations were removed from the active tree before Milestone 3
restarts. Their history remains available through git and is described in
[`old_code/README.md`](old_code/README.md).

Read [`STATUS.md`](STATUS.md) for the current durable project position.

## Documentation

- [`docs/product_roadmap.md`](docs/product_roadmap.md) — governing product meaning,
  development criteria, and milestone sequence.
- [`docs/decisions/project_decisions.md`](docs/decisions/project_decisions.md) —
  accepted cross-milestone technical decisions.
- [`docs/milestones/README.md`](docs/milestones/README.md) — milestone-gate rules.
- [`docs/controller/README.md`](docs/controller/README.md) — controller lifecycle,
  ownership, algorithms, and API reference.
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
