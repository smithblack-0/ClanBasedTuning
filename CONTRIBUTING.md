# Contributing

## Environment

The repository uses a standard `src/` package layout and `pyproject.toml`. `uv` is the
preferred development frontend, but ordinary virtual environments and `pip` are supported.

```bash
uv sync --extra dev --extra ray
```

or:

```bash
python -m pip install -e '.[dev,ray]'
```

## Checks

Run the relevant checks before committing:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m build
```

`python -m build` verifies that the repository can produce distribution artifacts locally;
the current CI still exercises an editable install and does not yet make a wheel/sdist
installation support claim.

## Test priorities

Tests should protect behavior at the narrowest useful level:

- unit tests for deterministic policy, validation, and state-machine behavior;
- framework contracts for Ray/Lightning/PyTorch extension seams and lifecycle assumptions;
- end-to-end contracts for user-visible Clan behavior such as repeated generation
  transition, full checkpoint continuation, and experiment restoration.

Do not add tests whose main purpose is to freeze filenames, example source text, or an
obsolete architecture. Examples should be runnable user material, not a second test harness.
A support claim should have direct executable evidence at the relevant framework/hardware
boundary rather than being inferred from a neighboring test.

## Design boundary

Do not add training-framework replacements. New code should either establish a small
reusable Clan-specific contract or adapt that contract to an existing framework extension
point. Framework lifecycle, launch, logging, precision, ordinary checkpoint behavior,
resource assignment, and user optimizer/model policy remain with their native owners unless
Clan semantics demonstrate a specific incompatibility.

CBT may select and mutate Tune config values, but user code owns their meaning and
application. Production CBT must not introduce an optimizer schema, inferred config-to-state
mapping, application callback, or post-load genome hook without an explicit product-contract
change.

## Repository hygiene

Git history is the archive for deleted experiments and superseded implementations. Keep
active documentation for current architecture, contracts, qualification evidence, and
maintainer guidance; do not retain placeholder `old_code`, empty scratchwork directories, or
negative tests solely to memorialize previous development stages.
