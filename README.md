# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: distributed training
that shares gradients across a population while adapting optimizer hyperparameters
online through population selection.

## Current package surface

The package currently exposes:

- `ClanController`, a thin worker-side object that stores one local fitness and caches
  whether that worker is the checkpoint source; and
- `MutationSpec`, a bounded linear or logarithmic mutation rule.

The repository also contains internal implementation pieces:

- the shared deterministic winner-selection function;
- scheduler-owned configuration type aliases; and
- a Ray GLOO population runtime that returns complete fitness associated with stable
  member identity.

The Ray runtime has direct CPU/GLOO component evidence, but the accepted public
`make_cbt_controller(genome=...)` factory is not implemented yet. Ordinary users cannot
yet obtain a fully wired controller inside a Tune training function.

## Accepted work not yet implemented

The accepted design still requires:

- selected-worker checkpoint provenance through `save_genome(checkpoint)`;
- a CBT Tune scheduler that owns the authoritative generation transition;
- Lightning/PyTorch integration for shared gradients, selected persistence, restoration,
  and target optimizer-configuration application;
- public worker construction that hides population-runtime wiring; and
- a repeated real multi-member workflow.

The scheduler's exact Ray superclass, delegated native machinery, and hook path remain
open to direct framework evidence.

## Documentation

Start with [`docs/README.md`](docs/README.md). The governing product roadmap is
[`docs/product_roadmap.md`](docs/product_roadmap.md), the accepted public lowering is in
[`docs/api.md`](docs/api.md), current implementation state is in [`STATUS.md`](STATUS.md),
and the active work sequence is [`docs/plan.md`](docs/plan.md).

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
