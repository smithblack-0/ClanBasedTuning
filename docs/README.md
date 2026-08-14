# ClanBasedTuning documentation

This is the active documentation entry point.

## Governing product direction

- [`product_roadmap.md`](product_roadmap.md) defines Clan Tuning, the project goals, the
  userspace genome-ownership boundary, and the stable criteria by which development is
  judged.

## Current design and contracts

- [`design/integration.md`](design/integration.md) defines the implemented initial
  Ray/Lightning/PyTorch lifecycle and responsibility boundaries.
- [`contracts/system_behavior.md`](contracts/system_behavior.md) states the observable
  behavior a complete Clan Tuning integration must produce.
- [`contracts/population_resolution_invariants.md`](contracts/population_resolution_invariants.md)
  states what the pre-report population boundary and next-generation assignment must
  preserve.
- [`contracts/population_resolution_responsibilities.md`](contracts/population_resolution_responsibilities.md)
  assigns ownership at that boundary for the initial DDP implementation.

## Public API

- [`api.md`](api.md) documents the implemented Ray Tune function API, including the
  explicit userspace Lightning checkpoint/application pattern. CBT supplies genomes; user
  code owns their meaning and application.

## Implementation evidence

- [`implementation/framework_managed_distributed_context.md`](implementation/framework_managed_distributed_context.md)
  records the foundation for one Tune trial/member/process/rank while retaining
  Lightning/PyTorch ownership of the distributed lifecycle.
- [`qualification/framework_managed_distributed_context.md`](qualification/framework_managed_distributed_context.md)
  records the narrower distributed-environment qualification that preceded the complete
  integration.
- [`qualification/function_api.md`](qualification/function_api.md) records direct evidence
  for the current complete two-generation single-node CPU function path, including shared
  gradients, winner-only checkpoint persistence, full continuation restore, userspace
  genome use, and independent mutation of every next member.

## Current state and next work

- Root [`STATUS.md`](../STATUS.md) records what the repository implements and qualifies now.
- [`plan.md`](plan.md) sequences the next work: evaluation comparability, cohort/failure
  hardening, GPU qualification, multi-node qualification, and later scientific/scaled
  evidence.
- Code and tests remain authoritative for executable behavior.

## Engineering process

- [`llm/README.md`](llm/README.md) routes substantial engineering and writing work.
- [`reviews/framework_native_review.md`](reviews/framework_native_review.md) checks that
  Clan-specific behavior remains narrow and framework-native.

## Non-active material

Completed and superseded records live under [`archive/`](archive/) and do not compete with
current authority. Tentative reasoning belongs under [`scratchwork/`](scratchwork/) until
accepted in the artifact that owns it.
