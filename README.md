# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: distributed training
that shares gradients across a population while adapting optimizer hyperparameters
online through population selection.

## Current package surface

The package currently exposes:

- `ClanController`, a thin worker-side object that stores one local fitness and caches
  whether that worker is the checkpoint source; and
- `MutationSpec`, a bounded linear or logarithmic mutation rule.

The current controller still receives an injected `exchange_fitness` callback. That is a
framework-independent test seam, not the production Ray population runtime.

The repository also contains the shared deterministic winner-selection function and
plain scheduler-state type aliases as internal implementation pieces.

## Accepted work not yet implemented

The accepted design requires:

- a Ray collective population runtime with explicit stable-member association;
- a selected-worker checkpoint and producer-provenance path;
- one Tune-side authoritative generation transition;
- Lightning/PyTorch integration for shared gradients, selected persistence, restoration,
  and target optimizer-configuration application; and
- a repeated real multi-member workflow.

The Tune integration may use a scheduler specialization or another narrow native adapter.
That internal choice remains open to direct Ray evidence.

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
