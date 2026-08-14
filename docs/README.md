# ClanBasedTuning documentation

This directory separates the public usage path, the current implementation design, and the
evidence supporting each compatibility claim.

## User path

- [`../README.md`](../README.md) gives installation and the shortest complete usage path.
- [`api.md`](api.md) explains the public API and lifecycle in detail.
- [`../examples/function_api.py`](../examples/function_api.py) is the runnable CPU example.
- [`../STATUS.md`](../STATUS.md) records what is actually qualified now.

## Product and architecture

- [`product_roadmap.md`](product_roadmap.md) defines Clan Tuning and the durable project goals.
- [`contracts/system_behavior.md`](contracts/system_behavior.md) states observable Clan
  behavior independently of framework hooks.
- [`contracts/population_resolution_invariants.md`](contracts/population_resolution_invariants.md)
  defines the complete-population generation boundary.
- [`contracts/population_resolution_responsibilities.md`](contracts/population_resolution_responsibilities.md)
  assigns ownership at that boundary.
- [`design/integration.md`](design/integration.md) records the current Ray/Lightning/PyTorch
  composition.

## Implementation evidence

- [`implementation/framework_managed_distributed_context.md`](implementation/framework_managed_distributed_context.md)
  records the externally launched Lightning DDP topology.
- [`implementation/ray_scheduler_compatibility.md`](implementation/ray_scheduler_compatibility.md)
  explains the owned synchronous scheduler and its narrow Ray compatibility seam.
- [`qualification/function_api.md`](qualification/function_api.md) defines the executable
  repeated-generation and restore qualification.
- [`qualification/framework_managed_distributed_context.md`](qualification/framework_managed_distributed_context.md)
  records the foundational cross-trial DDP evidence.

## Maintainer process

- [`plan.md`](plan.md) is the current corrective/production work sequence.
- [`reviews/framework_native_review.md`](reviews/framework_native_review.md) is the standing
  framework-ownership review.
- [`llm/README.md`](llm/README.md) routes substantial engineering and writing work.
