# ClanBasedTuning documentation

This directory separates the public usage path, implementation design, executable evidence,
and release/readiness process.

## User path

- [`../README.md`](../README.md) gives installation, the shortest complete usage path, and
  local qualification commands.
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
- [`design/integration.md`](design/integration.md) records the Ray/Lightning/PyTorch composition.

## Qualification

- [`qualification/function_api.md`](qualification/function_api.md) records repeated-generation
  and restore evidence.
- [`qualification/framework_managed_distributed_context.md`](qualification/framework_managed_distributed_context.md)
  records the foundational cross-trial DDP evidence.
- [`qualification/hardware.md`](qualification/hardware.md) gives the executable CUDA/NCCL,
  physical multi-node, and destructive peer-failure procedures.
- [`qualification/performance.md`](qualification/performance.md) defines the tiny measurement
  harness and what would count as performance evidence.
- [`qualification/observability.md`](qualification/observability.md) records the operational
  diagnostics available from the package.

## Implementation evidence

- [`implementation/framework_managed_distributed_context.md`](implementation/framework_managed_distributed_context.md)
  records the externally launched Lightning DDP topology.
- [`implementation/ray_scheduler_compatibility.md`](implementation/ray_scheduler_compatibility.md)
  explains the owned synchronous scheduler and narrow Ray compatibility seam.

## Release and maintainer process

- [`plan.md`](plan.md) is the ordered readiness gate sequence.
- [`releasing.md`](releasing.md) is the release checklist and evidence policy.
- [`reviews/framework_native_review.md`](reviews/framework_native_review.md) is the standing
  framework-ownership review.
- [`reviews/readiness_quality_audit.md`](reviews/readiness_quality_audit.md) records the final
  style/quality audit once all preceding gates are synchronized.
- [`llm/README.md`](llm/README.md) routes substantial engineering and writing work.
