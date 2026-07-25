# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient
training with member-local optimizer hyperparameters and population selection.

## Project status

The framework-independent Clan controller is the first accepted implementation
surface. Existing Ray/Lightning integration source and examples remain
proof-of-concept evidence rather than an accepted construction API.

Read [`STATUS.md`](STATUS.md) for the current durable project position.

## Documentation

- [`docs/product_roadmap.md`](docs/product_roadmap.md) — governing product meaning,
  development criteria, and milestone sequence.
- [`docs/decisions/project_decisions.md`](docs/decisions/project_decisions.md) —
  accepted cross-milestone technical decisions.
- [`docs/milestones/README.md`](docs/milestones/README.md) — milestone-gate rules
  and links to the active gate.
- [`docs/controller/README.md`](docs/controller/README.md) — controller lifecycle,
  ownership, algorithms, and API reference.
- [`docs/framework_alignment/README.md`](docs/framework_alignment/README.md) —
  framework research, evidence, and accepted responsibility model.
- [`AGENTS.md`](AGENTS.md) — entry point for coding agents and contributors using
  the repository's durable engineering process.

## [TODO] Accepted construction and integration API

The milestone that accepts a Ray/Lightning construction and integration contract
will publish the corresponding usage guide. Until then, existing integration
classes and examples should be read as implementation evidence rather than user
contracts.

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
