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

## Public lowering

- [`api.md`](api.md) records the current and accepted intended public surface while
  leaving internal helpers, population-exchange collaborators, framework hooks, and
  metadata representation free to evolve.

## Current implementation choice and evidence boundary

- [`implementation/framework_managed_distributed_context.md`](implementation/framework_managed_distributed_context.md)
  defines the initial one-trial/one-member/one-DDP-rank direction while retaining
  Lightning/PyTorch ownership of distributed lifecycle.
- [`qualification/framework_managed_distributed_context.md`](qualification/framework_managed_distributed_context.md)
  states what real Tune, Lightning, DDP, population, and failure evidence must exist
  before that path is supported.

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
