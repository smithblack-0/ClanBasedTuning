# ClanBasedTuning project status

Last updated: 2026-08-01

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

- trial execution and native resource and scheduler lifecycle to Ray Tune;
- complete-Clan coordination, stable member assignment, evolution, and atomic generation
  transition to a CBT Tune scheduler;
- externally launched distributed setup, training cadence, validation, restoration, and
  checkpoint construction to Lightning;
- process-group lifecycle, collectives, model synchronization, and shared gradients to
  native PyTorch DDP for the initial path;
- population fitness exchange to a narrow collaborator using that already-established
  framework-managed distributed context;
- deterministic selection and mutation behavior to framework-independent policy
  functions; and
- one local fitness, cached save decision, and winner provenance to `ClanController`.

One live Tune trial represents one stable Clan member and one DDP rank in the initial
path. ClanBasedTuning supplies the missing cohort identity and topology facts but does not
create or tear down a separate population process group.

The scheduler's existence and evolutionary authority are accepted. Its exact Ray
superclass, cohort-admission mechanism, delegated native machinery, and hook path remain
open to direct framework evidence. No persistent evolutionary controller exists beside
it.

## Not yet implemented

The repository does not yet contain:

- the production Tune-trial-to-Lightning DDP cohort integration;
- the framework-managed population exchange;
- selected-worker checkpoint provenance;
- the CBT Tune scheduler;
- member-local optimizer application for a qualified live path;
- a repeated real multi-member Clan workflow; or
- the later ClanFSDP topology.

## Current work

[`docs/plan.md`](docs/plan.md) begins by directly establishing the one-trial,
one-member, one-DDP-rank topology through real Ray Tune, Lightning, and PyTorch framework
seams. Population resolution then uses that established context rather than creating a
second Ray collective group.

The rejected standalone Ray/GLOO population-runtime branch was closed without merge. Its
process-group ownership model is not active implementation or accepted evidence.

Later steps connect population selection, selected checkpointing, the scheduler-owned
generation transition, complete Lightning/PyTorch training behavior, and a repeated manual
workflow. ClanFSDP remains a later separate extension.

The governing product direction remains [`docs/product_roadmap.md`](docs/product_roadmap.md).
Current design and contracts are indexed by [`docs/README.md`](docs/README.md).
