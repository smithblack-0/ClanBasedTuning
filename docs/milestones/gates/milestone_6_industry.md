# Milestone 6 gates — industry readiness

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

ClanBasedTuning is usable for serious industry workloads within a clearly
declared, directly qualified, and operationally diagnosable support envelope.

## Gates

### M6.1 The supported operating envelope is explicit

- Supported framework versions, hardware, topology, storage, precision, loader,
  optimizer, and model-wrapping configurations are published.
- Every support claim is backed by direct accelerator and failure-boundary
  evidence.
- Unsupported configurations fail early with actionable diagnostics.

### M6.2 Logging and observability explain the Clan lifecycle

- Records identify trial/member identity, population boundary, selected parent,
  target configurations, checkpoint lineage, optimizer reconciliation, and
  collective outcome.
- Logs and metrics support diagnosis without reproducing framework-owned state or
  creating a second source of truth.
- The operational meaning and retention of emitted records are documented.

### M6.3 Failure and restoration are production-qualified

- Persistent storage retains the experiment state and all required trial
  checkpoints.
- Cluster, node, process, and member failures are exercised within the declared
  envelope.
- Restoration works after completed boundaries and interruptions during a
  partially assembled synchronous boundary, building on the functional tests
  from Milestones 2 and 3.
- Failure either restores one coherent Clan state or terminates clearly; it does
  not continue with mixed generations or a silently reduced population.
- Recovery procedures, limits, and operator actions are documented.

### M6.4 Model-sharded training is framework-native

- FSDP and any other claimed Lightning-native sharding technology use their
  native lifecycle and checkpoint semantics.
- Clan-specific additions remain narrow and do not introduce a separate
  enterprise training implementation.
- Shared-gradient meaning, member divergence, checkpoint inheritance, optimizer
  reconciliation, and failure behavior remain correct under each claimed
  sharding mode.

### M6.5 Performance and scale are characterized honestly

- Scaled examples and measurements report throughput, memory, checkpoint cost,
  population overhead, and failure/recovery behavior for the declared envelope.
- Performance claims distinguish framework overhead, Clan algorithm cost, and
  workload characteristics.
- Scientific examples use the public package and expose limitations as well as
  promising behavior.

### M6.6 An independent team can operate the system

- Deployment, storage, monitoring, restoration, diagnosis, and troubleshooting
  documentation are sufficient for an independent engineering team.
- The industry-readiness audit exercises the complete public path rather than a
  private or specially simplified implementation.
- All inherited deferrals from earlier milestone gate files are either closed by
  evidence or explicitly removed from the supported product envelope.

## Closure evidence

Milestone 6 closes only after the industry-readiness audit, declared support
matrix, accelerator integration tests, restoration/failure tests, scaled public
examples, and operator documentation agree on one support envelope.
