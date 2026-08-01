# ClanBasedTuning project status

Last updated: 2026-07-31

## Current implementation

The active package contains:

- `ClanController`, with one local fitness, one injected population exchange, and one
  cached checkpoint-source decision;
- the shared deterministic winner-selection function;
- `MutationSpec`; and
- scheduler-owned configuration type aliases.

The current tests establish the framework-independent controller lifecycle, stable tie
behavior, finite-fitness requirements, mutation behavior, and the intentionally small
package surface.

## Accepted design

The current integration design assigns:

- native shared-gradient execution to PyTorch DDP;
- training cadence, validation, restoration, and checkpoint construction to Lightning;
- trial execution and native scheduler lifecycle to Ray Tune;
- pre-report complete-population communication to a Ray collective runtime;
- deterministic selection and mutation behavior to framework-independent policy
  functions;
- one local fitness and cached save decision to `ClanController`; and
- the authoritative complete generation transition to a CBT Tune scheduler.

The scheduler's existence and evolutionary authority are accepted. Its exact Ray
superclass, delegated native machinery, and hook path remain open. No persistent
evolutionary controller exists beside it.

## Not yet implemented

The repository does not yet contain:

- the production Ray population runtime;
- selected-worker checkpoint provenance;
- the CBT Tune scheduler;
- the Lightning/PyTorch Clan integration;
- optimizer-configuration application for a qualified live path; or
- a repeated real multi-member Clan workflow.

## Current work

[`docs/plan.md`](docs/plan.md) begins with replacing the transitional
`exchange_fitness` callback by the accepted Ray all-gather population runtime and its
direct qualification. Later steps connect selected checkpointing, the scheduler-owned
generation transition, Lightning/PyTorch training, and a repeated manual workflow.

The governing product direction remains [`docs/product_roadmap.md`](docs/product_roadmap.md).
Current design and contracts are indexed by [`docs/README.md`](docs/README.md).
