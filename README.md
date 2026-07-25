# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient
training with member-local optimizer hyperparameters and population selection.

## Project status

The current source and examples are proof-of-concept evidence. They are not an
accepted architecture or stable public API.

Read [`STATUS.md`](STATUS.md) for the current durable project position.

## Documentation

- [`docs/product_roadmap.md`](docs/product_roadmap.md) — governing product meaning,
  development criteria, and milestone sequence.
- [`docs/decisions/project_decisions.md`](docs/decisions/project_decisions.md) —
  accepted cross-milestone technical decisions.
- [`docs/milestones/README.md`](docs/milestones/README.md) — milestone-gate rules
  and links to the active gate.
- [`docs/framework_alignment/README.md`](docs/framework_alignment/README.md) —
  framework research, evidence, and accepted responsibility model.
- [`AGENTS.md`](AGENTS.md) — entry point for coding agents and contributors using
  the repository's durable engineering process.

## [TODO] Accepted public API and usage

The milestone that accepts a public construction and integration contract will
publish the corresponding API reference and usage guide. Until then, existing
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
