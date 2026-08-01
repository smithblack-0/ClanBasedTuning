# ClanBasedTuning documentation

This is the active documentation entry point.

## Governing product direction

- [`product_roadmap.md`](product_roadmap.md) defines Clan Tuning, the project goals, and
  the stable criteria by which development is judged.

## Current accepted design

- [`design/integration.md`](design/integration.md) defines the current framework lifecycle,
  state authority, and deliberately open integration surface.
- [`contracts/system_behavior.md`](contracts/system_behavior.md) states the observable
  behavior of a complete Clan Tuning integration.
- [`contracts/population_resolution_invariants.md`](contracts/population_resolution_invariants.md)
  states what the pre-report population boundary must preserve.
- [`contracts/population_resolution_responsibilities.md`](contracts/population_resolution_responsibilities.md)
  assigns ownership at that boundary.

## Current implementation choice and evidence boundary

- [`implementation/ray_population_resolution.md`](implementation/ray_population_resolution.md)
  chooses the first Ray collective mechanism without turning it into architecture.
- [`qualification/ray_population_resolution.md`](qualification/ray_population_resolution.md)
  states what must be demonstrated before a backend, device, or topology is supported.

## Current work

- [`plan.md`](plan.md) sequences the present implementation work.
- Root [`STATUS.md`](../STATUS.md) records what the repository actually implements now.
- Code and tests remain authoritative for current executable behavior.

## Engineering process

- [`llm/README.md`](llm/README.md) routes substantial engineering and writing work.
- [`reviews/framework_native_review.md`](reviews/framework_native_review.md) checks that
  Clan-specific behavior remains narrow and framework-native.

## Non-active material

Completed and superseded records live under [`archive/`](archive/) and do not compete
with current authority. Tentative reasoning belongs under [`scratchwork/`](scratchwork/)
until accepted in the artifact that owns it.
