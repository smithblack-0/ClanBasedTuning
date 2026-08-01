# ClanBasedTuning status

Last updated: 2026-07-31

## Current position

Milestone 1 framework research and Milestone 2 framework-independent selection/mutation work are complete historical foundations.

Milestone 3 is active. The accepted architecture uses:

- one Tune trial per live Clan member;
- one Lightning DDP world for shared-gradient training;
- Ray collective population resolution before reporting;
- one shared framework-independent winner policy;
- a thin worker controller with a cached local checkpoint-source decision;
- winner-side producer-genome annotation before checkpoint publication; and
- a CBT Tune scheduler as the sole authority over mutation, lineage, recovery, target genomes, and checkpoint redistribution.

See [`docs/architecture.md`](docs/architecture.md) and the active [`Milestone 3 contract`](docs/contracts/milestone_3.md).

## Implemented now

The package contains:

- `ClanController` with one local finite fitness, one injected fitness exchange, shared winner selection, and cached local save decision;
- `select_winner_id()` with minimizing, maximizing, and stable tie behavior;
- `MutationSpec` with bounded linear and logarithmic mutation; and
- scheduler dictionary aliases.

The current controller callback accepts a rank-ordered fitness sequence. It is a framework-independent predecessor, not the accepted production Ray runtime.

## Accepted but not implemented

- Ray all-gather population runtime with explicit stable-member association and direct CPU/CUDA qualification;
- integration factory that hides Ray membership and collective wiring from the user function;
- copied current-genome state on the controller;
- winner-only `save_genome(checkpoint)` using `{schema_version, member_id, genome}` metadata;
- CBT Tune scheduler generation barrier, winner verification, mutation, persistence, target assignment, and checkpoint redistribution;
- Lightning checkpoint and DDP integration; and
- repeated end-to-end generations through the real Tune and Lightning path.

## Next implementation order

1. Replace the inherited `exchange_fitness` boundary from the accepted Ray population-runtime contract, including names, docstrings, unit contracts, and real collective qualification.
2. Add controller-held copied genome provenance and winner-only checkpoint annotation without introducing a second collective.
3. Add the public worker integration factory.
4. Implement the CBT Tune scheduler transition and recovery contract.
5. Integrate Lightning DDP checkpoint persistence and restoration.
6. Prove at least two real generations and document the resulting support envelope.

Each item should be delivered as a coherent review unit; completion of one does not imply completion of Milestone 3.

## Current limitations

There is no active production Ray collective, public factory, Tune scheduler, Lightning integration, optimizer-configuration application system, or supported end-to-end workflow.

Hardware, backend, and topology support remain unclaimed until direct qualification satisfies [`docs/implementation/population_resolution.md`](docs/implementation/population_resolution.md).

## Reader path

- [`docs/README.md`](docs/README.md) — documentation index and authority.
- [`docs/decisions.md`](docs/decisions.md) — accepted cross-milestone decisions.
- [`docs/contracts/population_resolution.md`](docs/contracts/population_resolution.md) — worker population boundary.
- [`docs/contracts/system_behavior.md`](docs/contracts/system_behavior.md) — observable end-to-end outcomes.
- [`docs/evidence/framework.md`](docs/evidence/framework.md) — version-sensitive framework evidence.
