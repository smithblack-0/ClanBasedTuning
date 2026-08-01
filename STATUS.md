# ClanBasedTuning project status

Last updated: 2026-08-01

## Current implementation

The active package contains:

- `ClanController`, with one local fitness, one injected population exchange, and one
  cached checkpoint-source decision;
- the shared deterministic winner-selection function;
- `MutationSpec`;
- scheduler-owned configuration type aliases; and
- an internal Lightning `ClusterEnvironment` that presents externally assigned Tune
  member topology without owning distributed initialization, backend choice, collective
  execution, or process-group release.

The current tests establish the framework-independent controller lifecycle, stable tie
behavior, finite-fitness requirements, mutation behavior, and the intentionally small
public package surface.

A real framework contract additionally establishes one narrow distributed seam on Ray
2.56.1, Lightning 2.6.5, PyTorch 2.10.0, Python 3.11, and single-node CPU:

- two concurrent Tune function trials act as two stable Clan members;
- each trial is one externally launched Lightning process and one DDP rank;
- Lightning/PyTorch initialize one GLOO DDP world from the supplied topology;
- distinct local gradients reduce to one common gradient; and
- the externally launched Tune trial process owns final release after `Trainer.fit()`
  returns with the process group still active.

The GLOO choice belongs to the CPU qualification harness. Production code does not choose
GLOO or call process-group initialization or release APIs.

## Accepted design

The current integration design assigns:

- trial execution and native resource and scheduler lifecycle to Ray Tune;
- complete-Clan coordination, stable member assignment, evolution, and atomic generation
  transition to a CBT Tune scheduler;
- externally launched distributed setup, training cadence, validation, restoration, and
  checkpoint construction to Lightning;
- process-group lifecycle, collectives, model synchronization, and shared gradients to
  the qualified Lightning/PyTorch and external trial-process lifecycle for the initial
  path;
- population fitness exchange to a narrow collaborator using that already-established
  framework-managed distributed context;
- deterministic selection and mutation behavior to framework-independent policy
  functions; and
- one local fitness, cached save decision, and winner provenance to `ClanController`.

One live Tune trial represents one stable Clan member and one DDP rank in the initial
path. ClanBasedTuning supplies the missing cohort identity and topology facts but does not
create or release a separate population process group.

The scheduler's existence and evolutionary authority are accepted. Its exact Ray
superclass, cohort-admission mechanism, delegated native machinery, and hook path remain
open to direct framework evidence. No persistent evolutionary controller exists beside
it.

## Not yet implemented

The repository does not yet contain:

- complete-cohort admission and production assignment of rank, world-size, rendezvous,
  member, and cohort identity;
- coherent repeated-round lifecycle over one live Tune-member DDP cohort;
- the framework-managed population exchange;
- selected-worker checkpoint provenance;
- the CBT Tune scheduler;
- member-local optimizer application for a qualified live path;
- a repeated real multi-member Clan workflow; or
- the later ClanFSDP topology.

The current two-member contract assumes that the complete cohort is already schedulable
and supplies its rendezvous facts from the test harness. It does not qualify incomplete
cohort behavior, failures, CUDA/NCCL, or multi-node execution.

## Current work

[`docs/plan.md`](docs/plan.md) next resolves complete-cohort admission and production
assignment of the topology facts consumed by the qualified Lightning environment.
Population resolution then uses that established context rather than creating a second
Ray collective group.

The rejected standalone Ray/GLOO population-runtime branch was closed without merge. Its
process-group ownership model is not active implementation or accepted evidence.

Later steps connect population selection, selected checkpointing, the scheduler-owned
generation transition, complete Lightning/PyTorch training behavior, and a repeated manual
workflow. ClanFSDP remains a later separate extension.

The governing product direction remains [`docs/product_roadmap.md`](docs/product_roadmap.md).
Current design and contracts are indexed by [`docs/README.md`](docs/README.md).
