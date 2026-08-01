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

- ordinary distributed gradients to PyTorch;
- training, restoration, and checkpoint construction to Lightning;
- trial execution and native scheduler lifecycle to Ray Tune;
- pre-report complete-population communication to a Ray collective runtime;
- deterministic selection and mutation to framework-independent policy functions;
- one local fitness and cached save decision to `ClanController`; and
- the authoritative complete generation transition to the CBT Tune integration.

The Tune seam may be a scheduler specialization or another narrow native adapter. No
persistent evolutionary controller exists beside it.

## Not yet implemented

The repository does not yet contain:

- the production Ray population runtime;
- selected-worker checkpoint provenance;
- the CBT Tune generation transition;
- the Lightning/PyTorch Clan integration;
- optimizer-configuration application for a qualified live path; or
- a repeated real multi-member Clan workflow.

## Current work

[`docs/plan.md`](docs/plan.md) begins with replacing the transitional
`exchange_fitness` callback by the accepted Ray all-gather population runtime and its
direct qualification. Later steps connect selected checkpointing, Tune-side transition,
Lightning/PyTorch training, and a repeated manual workflow.

The governing product direction remains [`docs/product_roadmap.md`](docs/product_roadmap.md).
Current design and contracts are indexed by [`docs/README.md`](docs/README.md).
