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

## Normal checks

Run the repository checks before committing:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src/clan_based_tuning --show-error-codes
python -m pytest
python -m build
python -m twine check dist/*
```

The distribution test also builds and checks wheel/sdist artifacts from pytest. The direct
commands remain useful when preparing a release candidate.

The Ray/Lightning end-to-end contracts are materially slower than pure unit tests but are
required evidence for changes to scheduler, runtime, distributed, checkpoint, or restore
behavior.

## Local hardware qualification

The hardware tests use the repository's tiny synthetic MLP/AdamW workload; they do not fetch
a model or dataset.

Two visible CUDA GPUs are sufficient for the local CUDA/NCCL contract:

```bash
python -m pytest tests/hardware/test_cuda_function_path.py -vv
```

Physical multi-node and destructive participant-failure qualification require explicit opt-in
and environment setup. Follow [`docs/qualification/hardware.md`](docs/qualification/hardware.md)
rather than weakening those tests to run accidentally in ordinary CI.

Measure the complete tiny function path with:

```bash
python benchmarks/tiny_function_path.py --generations 3
```

Treat its output as evidence to record and compare, not as an arbitrary universal performance
threshold.

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

## Documentation as a design check

Docstrings and comments preserve knowledge that is expensive to reconstruct from the code;
they are not a coverage target. A useful docstring explains a non-obvious contract, ownership
boundary, lifecycle/order constraint, failure mode, compatibility reason, or invariant.

If a private helper's best explanation merely restates its name, arguments, return value, or
obvious implementation, first ask whether the helper should be inlined or removed. Small
framework-required overrides may still be necessary; document the framework assumption they
adapt or the failure the override prevents rather than writing a ceremonial getter description.

A practical review question is: **if this documentation disappeared, what maintenance knowledge
would become materially harder to recover?** If the answer is “none,” either improve the
explanation with real design information or reconsider the abstraction.

## Test priorities

Use the narrowest test that establishes the contract:

- pure unit tests for selection, mutation, generation resolution, and cohort state;
- framework contracts for Ray/Lightning/PyTorch lifecycle assumptions;
- small realistic end-to-end contracts for repeated generation transition and restoration;
- opt-in hardware contracts for claims that require unavailable hardware/topology; and
- distribution tests for the wheel users actually install.

Tests should describe intended behavior rather than preserve historical filenames, removed
APIs, or implementation shape. Difficulty testing a behavior in isolation is a reason to
reconsider its ownership boundary, not a reason to add broad patching.

## Release and review

The release procedure is in [`docs/releasing.md`](docs/releasing.md). A release claim must not
exceed its direct qualification evidence. A project license is an owner decision and remains
a hard release gate until selected.

Passing tests is not the end of a substantial change. The final readiness gate is a fresh
repository-wide review against the project's style and quality contract after code, tests,
docs, examples, packaging, and qualification records have been synchronized.
