# ClanBasedTuning

ClanBasedTuning explores optimizer hyperparameters across synchronous members that
share reduced gradients while retaining separate model and optimizer trajectories.

## Project status

This repository is pre-alpha. The product roadmap, accepted decisions, and milestone
gates are authoritative; proof-of-concept integration code is not a stable public API.

- [Product roadmap](docs/product_roadmap.md)
- [Current project status](STATUS.md)
- [Framework-alignment package](docs/framework_alignment/README.md)
- [Active Milestone 2 gate](docs/milestones/gates/milestone_2_evolutionary_subsystem.md)

## Current accepted subsystem

Milestone 2 introduces the framework-independent
[`ClanController`](docs/clan_controller.md). It initializes optimizer configurations,
selects the sole parent from a completed population, and emits the next population's
optimizer configurations using plain Python data.

```bash
python examples/clan_controller.py
```

## [TODO] Training integration API

The existing Ray, Lightning, DDP, checkpoint, and optimizer-application code remains
proof-of-concept evidence. Its construction API and usage contracts are intentionally
not documented here as accepted behavior while the milestone sequence replaces or
qualifies them.

## [TODO] User-facing configuration

A later milestone will define how Tune-facing parameter declarations, required
starting defaults, controller policy, and optimizer application compose into the
ordinary user workflow. Preliminary framework research belongs in
[`docs/llm/scratchwork/`](docs/llm/scratchwork/) and is non-authoritative.

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
