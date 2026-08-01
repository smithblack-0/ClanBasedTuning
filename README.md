# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient distributed training with member-local optimizer hyperparameters and population selection.

## Current package surface

The implemented framework-independent core currently contains:

- `ClanController`, which stores one local fitness, calls an injected fitness-exchange function, applies the shared winner selector, and caches whether the local member should provide the checkpoint;
- `select_winner_id()`, the deterministic minimizing/maximizing selector with stable lower-member tie behavior;
- `MutationSpec`, one bounded linear or logarithmic scalar mutation rule; and
- scheduler dictionary aliases.

The injected `exchange_fitness()` seam is an older local abstraction. It is not a production Ray collective and is scheduled for replacement from the accepted population-resolution contract.

Not yet implemented are:

- the Ray collective population runtime and public worker factory;
- controller-held genome provenance and winner-only `save_genome()`;
- the CBT Tune scheduler and durable generation transition;
- Lightning DDP checkpoint integration; and
- a qualified multi-generation end-to-end path.

Read [`STATUS.md`](STATUS.md) for the current work boundary and [`docs/README.md`](docs/README.md) for the authoritative documentation path.

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`AGENTS.md`](AGENTS.md) before substantial changes.
