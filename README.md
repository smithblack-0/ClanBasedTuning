# ClanBasedTuning

ClanBasedTuning is an early-stage Python package for making clan-based optimizer
hyperparameter tuning usable inside existing distributed training systems.

The intended training model is a single cooperative clan:

- each rank owns a separate model trajectory and optimizer state;
- ranks train on separate minibatches;
- gradients are reduced across the clan;
- each rank applies the shared gradient with rank-local optimizer hyperparameters;
- periodic fitness evaluation selects and reseeds the next clan generation.

The project is currently establishing its framework contracts. It does not yet
provide a usable tuning implementation.

## Planned surfaces

- a small raw PyTorch reference integration;
- a Lightning integration built around its distributed strategy and callback
  extension points;
- controller interfaces for optimizer hyperparameter mutation and selection;
- explicit state-transfer and checkpoint semantics for divergent replicas.

The package is intended to add focused functionality to existing frameworks,
not replace their training, launch, logging, or persistence systems.

## Development setup

Python 3.11 through 3.13 is supported by the package metadata.

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

PyTorch installation varies by accelerator and platform. For GPU development,
install the appropriate PyTorch build for the machine before syncing the rest
of the environment.

## Status

Pre-alpha. The public API and framework support policy are not yet defined.
