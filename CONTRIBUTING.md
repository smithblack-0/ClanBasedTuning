# Contributing

## Environment

The repository uses a standard `src/` package layout and `pyproject.toml`.
`uv` is the preferred development frontend, but ordinary virtual environments
and `pip` remain supported.

```bash
uv sync --extra dev
```

## Checks

Run these before committing:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Design boundary

Do not add training-framework replacements. New code should either establish a
small reusable clan-tuning contract or adapt that contract to an existing
framework. Framework lifecycle, launch, logging, precision, and ordinary
checkpoint behavior remain with the host framework unless clan divergence
makes a targeted override necessary.
