# ClanBasedTuning documentation

This is the documentation entry point for users and maintainers.

## Start with the user path

- [`../README.md`](../README.md) gives installation, the minimal function API, resource
  semantics, the scientific genome boundary, and interrupted-run restore.
- [`api.md`](api.md) is the detailed public API and lifecycle guide.
- [`../examples/function_api.py`](../examples/function_api.py) is the runnable two-member
  CPU mechanics example.
- Root [`STATUS.md`](../STATUS.md) separates the currently qualified behavior from broader
  repository/production-readiness gaps.

## Product and architecture

- [`product_roadmap.md`](product_roadmap.md) defines Clan Tuning, project goals, userspace
  ownership, and stable development criteria.
- [`design/integration.md`](design/integration.md) records the current Ray/Lightning/PyTorch
  integration and responsibility boundaries.
- [`contracts/system_behavior.md`](contracts/system_behavior.md) states observable complete
  Clan behavior.
- [`contracts/population_resolution_invariants.md`](contracts/population_resolution_invariants.md)
  and [`contracts/population_resolution_responsibilities.md`](contracts/population_resolution_responsibilities.md)
  define the generation boundary and ownership split.

## Evidence and support

- [`qualification/framework_managed_distributed_context.md`](qualification/framework_managed_distributed_context.md)
  records the original external Tune-member DDP seam qualification.
- [`qualification/function_api.md`](qualification/function_api.md) records direct evidence
  for the complete repeated function path and its current support envelope.
- [`implementation/framework_managed_distributed_context.md`](implementation/framework_managed_distributed_context.md)
  records framework evidence behind the topology/data/checkpoint seams.

## Maintainer process

- [`plan.md`](plan.md) sequences current work and repository-readiness requirements.
- [`reviews/framework_native_review.md`](reviews/framework_native_review.md) is the standing
  framework-ownership review.
- [`llm/README.md`](llm/README.md) contains the repository's engineering and technical-writing
  process used by coding agents and maintainers doing substantial work.

Git history, rather than an active archive or placeholder `old_code` tree, retains superseded
implementations and previous milestone records.
