# Milestone 6 gates — industry readiness

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

ClanBasedTuning is usable for serious industry workloads within a clearly
declared, directly qualified, documented, observable, and operationally
diagnosable support envelope. An independent engineering team can deploy,
restore, inspect, and troubleshoot the same public system exercised by tests and
examples.

## Capability and design gates

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
- The operational meaning, schema, destination, retention, and correlation of
  emitted records are explicit.

### M6.3 Failure and restoration are production-qualified

- Persistent storage retains the experiment state and all required trial
  checkpoints.
- Cluster, node, process, and member failures are handled within the declared
  envelope.
- Restoration works after completed boundaries and interruptions during a
  partially assembled synchronous boundary, building on the functional contracts
  from Milestones 2 and 3.
- Failure either restores one coherent Clan state or terminates clearly; it does
  not continue with mixed generations or a silently reduced population.

### M6.4 Model-sharded training is framework-native

- FSDP and any other claimed Lightning-native sharding technology use their
  native lifecycle and checkpoint semantics.
- Clan-specific additions remain narrow and do not introduce a separate
  enterprise training implementation.
- Shared-gradient meaning, member divergence, checkpoint inheritance, optimizer
  reconciliation, and failure behavior remain correct under each claimed
  sharding mode.

### M6.5 Performance and scale are characterized honestly

- Measurements report throughput, memory, checkpoint cost, population overhead,
  storage behavior, and failure/recovery cost for the declared envelope.
- Performance claims distinguish framework overhead, Clan algorithm cost, and
  workload characteristics.
- Qualification defines the scale at which each claim was measured rather than
  implying untested generality.

## Test and qualification gates

### M6.6 The support matrix is executable

For every claimed row in the support matrix, direct automated or repeatable
qualification covers the relevant combination of:

- framework and Python versions;
- accelerator and node topology;
- DDP or claimed model-sharding strategy;
- precision and accumulation mode;
- loader and evaluation configuration;
- optimizer layout and restoration path;
- storage backend and persistence behavior.

Untested combinations are absent from the supported envelope rather than inferred
from nearby results.

### M6.7 Failure-injection and restoration tests cover operating boundaries

Repeatable tests exercise:

- member process failure;
- worker or node loss where claimed;
- Ray actor and experiment interruption;
- storage unavailability or incomplete checkpoint visibility where relevant;
- interruption after a completed boundary and during a partial population
  boundary;
- restore from persistent storage into the declared recovery topology;
- explicit termination when one coherent Clan state cannot be reconstructed.

Tests verify both machine behavior and operator-visible diagnostics.

### M6.8 Model-sharding and accelerator tests prove semantic equivalence

For every claimed sharding or accelerator mode, tests prove:

- coherent initial state and shared-gradient behavior;
- member divergence under local optimizer policy;
- comparable member-local fitness;
- sole-parent checkpoint inheritance and optimizer reconciliation;
- collective failure and restoration semantics;
- compatibility with observability and diagnostics.

A smoke test that only starts training is insufficient.

### M6.9 Performance and regression tests protect the qualified envelope

- Benchmarks record throughput, peak memory, checkpoint latency and size,
  population overhead, and restoration time on named hardware and workloads.
- Repeatable thresholds or historical comparisons detect material regressions in
  the supported path.
- Performance tests do not hide correctness, diagnostics, or failure costs.
- Results include variance and workload context sufficient for honest comparison.

### M6.10 Observability tests prove diagnostic claims

- Required records are emitted exactly once at their authoritative lifecycle
  boundaries.
- Record schemas, identities, lineage, retention, and cross-system correlation
  are tested.
- Failure tests confirm that an operator can identify the affected member,
  boundary, source checkpoint, and recovery or termination outcome.

## Documentation gates

### M6.11 Operations documentation enables independent deployment and recovery

The milestone delivers:

- a published support matrix with exact versions, hardware, topology, storage,
  precision, loader, optimizer, and sharding boundaries;
- deployment and configuration guidance for every supported operating model;
- persistent-storage and checkpoint-retention guidance;
- monitoring, emitted-record, and alert interpretation reference;
- failure, restoration, rollback, and termination runbooks;
- troubleshooting organized by observable symptoms and authoritative lifecycle
  state;
- performance and capacity-planning guidance grounded in measured workloads;
- upgrade and compatibility guidance for version-sensitive framework seams.

An independent team must be able to operate the system without relying on the
original implementers or undocumented repository knowledge.

### M6.12 Engineering and scientific documentation remain honest

- Design documents explain every remaining custom seam and framework owner.
- Limitations, unsupported configurations, unresolved risks, and operational
  costs are published beside support claims.
- Scientific reports distinguish experimental findings from support
  qualification and do not turn promising results into architectural guarantees.

## Example and scientific-work gates

### M6.13 Scaled public examples exercise the declared support envelope

The project provides public, reproducible workloads that collectively cover:

- a serious multi-member accelerator training run;
- every claimed model-sharding mode;
- persistent checkpointing and restoration;
- observable parent selection, optimizer reconciliation, and lineage;
- at least one injected failure and documented recovery or clean termination.

Examples use the same public assembly path and components qualified by tests.

### M6.14 Operational examples teach diagnosis and recovery

At least one guided exercise starts from an observable failure, follows logs and
records to the authoritative state, performs the documented operator action, and
verifies the resulting recovery or termination. The exercise must be runnable by
an independent team.

### M6.15 Scientific examples characterize value and limits at scale

Scaled studies:

- use the public package and declared support envelope;
- report workload, population, optimizer-policy path, round cadence, compute and
  storage cost, throughput, failure/recovery behavior, and outcome;
- compare against relevant baselines without engineering a guaranteed favorable
  result;
- publish negative or neutral findings and known confounders;
- make artifacts sufficient for independent interpretation and reproduction.

## Evidence, review, and release gates

### M6.16 The industry-readiness audit covers the complete public path

The audit traces each support claim through implementation, tests, documentation,
examples, operational records, and observed failure behavior. It rejects private
or specially simplified paths that users cannot reproduce.

### M6.17 An independent team successfully operates the system

A team not responsible for the implementation uses only published artifacts to:

- deploy a supported workload;
- inspect a complete Clan lifecycle;
- diagnose an injected or naturally occurring failure;
- restore or terminate according to the runbook;
- interpret performance and scientific outputs;
- identify the boundary of supported behavior.

Observed documentation or diagnostic gaps block closure.

### M6.18 All inherited obligations are closed or removed from support

- Every deferral from Milestones 2 through 5 is linked to direct closure evidence
  or explicitly excluded from the published product envelope.
- Tests, documentation, examples, and support claims agree on the same final
  boundary.
- No unowned “later” work remains inside the claimed industry-ready product.

## Closure evidence

Milestone 6 closes only after the industry-readiness audit, executable support
matrix, accelerator and sharding suites, failure/restoration and observability
tests, performance results, operations documentation, scaled public examples,
scientific studies, independent-team exercise, and final human review agree on
one support envelope.
