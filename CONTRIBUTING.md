# Contributing

ClanBasedTuning is a framework integration project. Changes are judged by the behavior they
add and by whether responsibility remains with the framework or application that naturally
owns it.

## Environment

The package uses a standard `src/` layout and installs its Ray Tune, Lightning, and PyTorch
runtime dependencies by default because those frameworks are the usable product surface.

```bash
python -m pip install -e '.[dev]'
```

## Checks

Run the relevant checks before committing:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m build
```

The Ray/Lightning end-to-end contracts are materially slower than pure unit tests but are
required evidence for changes to scheduler, runtime, distributed, checkpoint, or restore
behavior.

## Design boundary

Ray Tune owns trial execution, resources, storage, and experiment restoration. Lightning and
PyTorch own the training loop, optimizer restoration, DDP, backend/device behavior, and
checkpoint construction. ClanBasedTuning owns only the Clan-specific population transition,
cohort identity/rendezvous facts that the frameworks cannot infer, and the small adapter
behavior required to connect those owners.

The current Tune config/genome belongs to user code. CBT may select and mutate its values,
but it must not infer what a key means, map keys to optimizer fields, or hide application in
a package callback. Examples and tests that demonstrate application keep those edits visibly
in userspace.

When a framework exposes no stable atomic operation required by Clan Tuning, prefer one
small, documented compatibility boundary over copying version-sensitive calls throughout the
system. The current Ray checkpoint/config transfer dependency is isolated in `ray_compat.py`;
changes there require direct framework qualification.

## Test priorities

Use the narrowest test that establishes the contract:

- pure unit tests for selection, mutation, generation resolution, and cohort state;
- framework contracts for Ray/Lightning/PyTorch lifecycle assumptions;
- end-to-end contracts for repeated generation transition and experiment restoration; and
- distribution tests for the wheel users actually install.

Tests should describe the intended behavior rather than preserve historical filenames,
removed APIs, or implementation shape. Difficulty testing a behavior in isolation is a
reason to reconsider its ownership boundary, not a reason to add broad patching.

## Repository hygiene

Git history is the archive for superseded implementations. Keep active documentation for
current contracts, evidence, support boundaries, and maintainer guidance; do not retain
placeholder modules or tests solely to memorialize old designs.
