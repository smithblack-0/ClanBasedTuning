# ClanBasedTuning documentation

This is the single active documentation entry point.

## Project authority

1. [`roadmap.md`](roadmap.md) defines product meaning, development criteria, and milestone sequence.
2. [`decisions.md`](decisions.md) records accepted cross-milestone technical decisions.
3. [`architecture.md`](architecture.md) defines the accepted Milestone 3 system lifecycle and state authority.
4. [`contracts/`](contracts/) states behavior and evidence that implementation must satisfy.
5. [`implementation/`](implementation/) records replaceable implementation choices and their qualification boundary.
6. [`evidence/`](evidence/) preserves version-sensitive framework observations used to justify claims.

The root [`STATUS.md`](../STATUS.md) states current implementation and active work. Code and tests establish current behavior; a planned API is not implemented merely because a design describes it.

## Active contracts

- [`contracts/system_behavior.md`](contracts/system_behavior.md) — end-to-end training outcomes.
- [`contracts/population_resolution.md`](contracts/population_resolution.md) — complete-population checkpoint-source resolution and ownership.
- [`contracts/milestone_3.md`](contracts/milestone_3.md) — the active milestone result and closure evidence.

## Current implementation decision

- [`implementation/population_resolution.md`](implementation/population_resolution.md) — the initial Ray collective mechanism and the evidence required before support is claimed.

## Working process

Engineering and writing workflows live under [`process/`](process/). Root [`AGENTS.md`](../AGENTS.md) is the contributor entry point.

Completed and superseded records live under [`archive/`](archive/) and are not active authority. Tentative reasoning belongs in `scratchwork/` only while useful.
