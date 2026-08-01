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
framework-independent test seam, not the production distributed integration.

The repository also contains the shared deterministic winner-selection function and
plain scheduler-state type aliases as internal implementation pieces.

## Accepted work not yet implemented

The accepted initial topology requires:

- one Ray Tune trial per stable Clan member;
- one externally launched Lightning process and native PyTorch DDP rank per member;
- framework-managed distributed setup and teardown rather than a package-owned
  population process group;
- population fitness exchange through that established distributed context;
- a selected-worker checkpoint and producer-provenance path;
- a CBT Tune scheduler that owns the authoritative generation transition;
- member-local optimizer application without erasing shared-gradient divergence; and
- a repeated real multi-member workflow.

The scheduler's exact Ray superclass, complete-cohort admission mechanism, delegated
native machinery, and hook path remain open to direct framework evidence.

A later ClanFSDP extension may add a composed model-shard and Clan-member topology. It is
not part of the initial DDP implementation.

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
