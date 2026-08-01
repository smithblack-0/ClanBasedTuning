# ClanBasedTuning project status

Last updated: 2026-08-01

## Current implementation

The active package contains:

- `ClanController`, with one local fitness, one member-associated population runtime,
  and one cached checkpoint-source decision;
- an internal Ray GLOO population runtime that all-gathers CPU `float64` fitness through
  an explicit stable-member-to-collective-rank mapping;
- the shared deterministic winner-selection function;
- `MutationSpec`; and
- scheduler-owned configuration type aliases.

The Ray runtime is initialized for the complete live population, may serve consecutive
population boundaries, and is destroyed when that population ends. Because Ray 2.56's
GLOO timeout does not bound an in-progress torch collective, the runtime exits the local
Ray actor when an all-gather exceeds its configured boundary rather than leaving the
worker blocked indefinitely.

Current tests establish:

- the framework-independent controller lifecycle;
- stable min/max and tie behavior;
- exact member association independent of collective rank order;
- preservation of adjacent Python `float64` fitness values;
- repeated population boundaries through one initialized group; and
- surfaced actor failure when a required member does not enter the all-gather.

## Accepted design

The current integration design assigns:

- native shared-gradient execution to PyTorch DDP;
- training cadence, validation, restoration, and checkpoint construction to Lightning;
- trial execution and native scheduler lifecycle to Ray Tune;
- pre-report complete-population communication to the Ray population runtime;
- deterministic selection and mutation behavior to framework-independent policy
  functions;
- one local fitness and cached save decision to `ClanController`; and
- the authoritative complete generation transition to a CBT Tune scheduler.

The scheduler's existence and evolutionary authority are accepted. Its exact Ray
superclass, delegated native machinery, and hook path remain open. No persistent
evolutionary controller exists beside it.

## Not yet implemented

The repository does not yet contain:

- the public `make_cbt_controller(genome=...)` factory or automatic population-runtime
  construction inside a Tune worker;
- selected-worker checkpoint provenance;
- the CBT Tune scheduler;
- the Lightning/PyTorch Clan integration;
- optimizer-configuration application for a qualified live path; or
- a repeated real multi-member Clan workflow.

The current Ray evidence qualifies only the internal CPU/GLOO component path. It does not
qualify CUDA/NCCL, Tune worker construction, checkpoint reporting, scheduler transition,
or end-to-end Clan execution.

## Current work

The first implementation slice in [`docs/plan.md`](docs/plan.md) has produced the
internal Ray population runtime and its initial CPU/GLOO qualification. The next slice is
the accepted selected-checkpoint producer-provenance path; public factory wiring remains
part of assembling the worker integration around these components.

The governing product direction remains [`docs/product_roadmap.md`](docs/product_roadmap.md).
Current design and contracts are indexed by [`docs/README.md`](docs/README.md).
