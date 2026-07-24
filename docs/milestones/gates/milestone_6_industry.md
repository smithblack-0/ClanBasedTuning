# Milestone 6 gates — industry readiness

Status: working rewrite for review

## Milestone result

ClanBasedTuning is usable for serious workloads within a clearly declared, directly qualified, observable, diagnosable, and operationally recoverable support envelope. An independent engineering team can deploy, inspect, restore, and troubleshoot the same public system exercised by tests and examples.

## Capability and responsibility gates

### M6.1 The supported operating envelope is explicit

Supported framework/Python versions, hardware, topology, storage, precision, loader, optimizer, model wrapping, and sharding configurations are published. Unsupported configurations fail early with actionable diagnostics.

### M6.2 Logging and observability explain the Clan lifecycle

Authoritative records identify member/trial identity, round boundary, parent, target configurations, checkpoint lineage, optimizer reconciliation, collective outcome, and failure/recovery result without creating a second source of framework state.

### M6.3 Persistent failure recovery is production-qualified

Within the declared envelope, persistent storage retains the experiment and trial state required to restore one coherent Clan after the supported cluster, node, process, or member failures. Restoration either resumes one valid population state or terminates clearly; mixed generations and silently reduced populations are invalid.

### M6.4 Claimed model-sharding modes remain framework-native

FSDP and any other supported native sharding strategy preserve shared-gradient meaning, member divergence, comparable fitness, parent-state inheritance, optimizer reconciliation, checkpoint semantics, and collective failure/recovery without a separate enterprise implementation.

### M6.5 Performance and scale are characterized honestly

Measurements state the named workload, hardware, topology, population, framework versions, throughput, memory, checkpoint/storage cost, population overhead, and recovery cost. Claims distinguish framework overhead, Clan algorithm cost, and workload effects.

## Test and qualification gates

### M6.6 Every support claim has direct qualification

The qualification matrix exercises every claimed combination of framework version, accelerator/topology, DDP or sharding mode, precision, data/evaluation configuration, optimizer layout, and storage/recovery path. Untested combinations are not inferred into the supported envelope.

### M6.7 Failure-injection and restoration tests cover operational boundaries

Repeatable tests exercise the claimed process, member, node, actor/experiment, storage, completed-boundary, and partial-boundary failures. They verify both machine behavior and operator-visible diagnostics.

### M6.8 Accelerator and sharding tests prove semantic equivalence

For every claimed mode, tests demonstrate coherent initial/parent state, common gradients, member divergence, comparable local fitness, sole-parent transition, optimizer reconciliation, checkpoint/restoration behavior, and observability.

### M6.9 Performance and observability tests protect the support envelope

Benchmarks detect material regressions in throughput, memory, checkpoint/storage, population overhead, and restoration time. Record-schema and correlation tests verify that an operator can identify the affected member, boundary, source state, and final outcome.

## Documentation gates

### M6.10 Operations documentation enables independent deployment and recovery

The milestone delivers the exact support matrix, deployment/configuration guidance, storage and retention guidance, record/monitoring reference, recovery/termination runbooks, symptom-oriented troubleshooting, performance/capacity guidance, and framework-upgrade compatibility guidance.

### M6.11 Engineering and scientific claims remain honest

Design documents explain every remaining custom seam. Limitations, unsupported configurations, operational costs, negative results, and unresolved risks appear beside the claims they bound.

## Example and scientific-work gates

### M6.12 Scaled public workloads exercise the declared envelope

Public reproducible workloads cover serious accelerator training, every claimed sharding mode, persistent checkpointing and restoration, observable transitions and lineage, and at least one injected failure with documented recovery or clean termination.

### M6.13 An operational exercise teaches diagnosis and recovery

An independent engineer starts from an observable failure, follows the published records to authoritative state, performs the documented action, and verifies recovery or termination.

### M6.14 Scientific studies characterize value and limits at scale

Studies use the public package and declared envelope, compare relevant baselines, report compute/storage/operational costs and confounders, and publish favorable, neutral, or unfavorable outcomes with sufficient artifacts for independent interpretation.

## Evidence, review, and release gates

### M6.15 The industry-readiness audit covers the complete public path

The audit traces every support claim through implementation, qualification tests, documentation, examples, records, and observed failure behavior. Private or specially simplified paths do not establish support.

### M6.16 An independent team successfully operates the system

A team not responsible for implementation deploys a supported workload, inspects a complete Clan lifecycle, diagnoses a failure, restores or terminates according to the runbook, interprets performance/scientific output, and identifies the support boundary. Any documentation or diagnostic gap blocks closure.

## Closure evidence

Milestone 6 closes only when the readiness audit, support matrix, accelerator/sharding and failure/recovery suites, performance and observability results, operations documentation, scaled examples, scientific studies, independent-team exercise, and human review agree on one support envelope.