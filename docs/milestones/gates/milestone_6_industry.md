# Milestone 6 gates — industry readiness

Status: proposed future milestone gate under Milestone 1 review

## Milestone result

ClanBasedTuning is usable for serious workloads within a clearly declared,
directly qualified, observable, diagnosable, and operationally recoverable
support envelope. An independent engineering team can deploy, inspect, restore,
and troubleshoot the same public system exercised by tests and examples.

This gate states the required industry result and major evidence. The exact
support matrix, failure taxonomy, and operational procedures are designed when
Milestone 6 becomes active.

## Capability and responsibility gates

### M6.1 The support envelope is explicit and evidence-bounded

Published support identifies the qualified framework and Python versions,
hardware, topology, storage, precision, data/evaluation behavior, optimizer
layouts, model wrapping, and native sharding modes. Unsupported configurations
fail early with actionable diagnostics.

No support row is inferred from a nearby configuration that was not directly
exercised.

### M6.2 Observability explains the Clan lifecycle

Authoritative records let an operator correlate trial/member identity, round
boundary, selected parent, resulting optimizer configurations, checkpoint
lineage, optimizer reconciliation, collective outcome, and failure or recovery
result without creating a second source of framework state.

### M6.3 Persistent failure recovery is qualified for the declared envelope

For every recovery behavior the support matrix claims, persistent framework
state is sufficient to restore one coherent Clan or the system terminates
clearly. Mixed generations and silently reduced populations are invalid.

The accepted failure taxonomy and tests follow the supported deployment design;
this gate does not precommit to every possible process, node, actor, or storage
failure before that design exists.

### M6.4 Claimed model-sharding modes remain framework-native

FSDP and any other supported Lightning-native sharding strategy preserve the
Clan mechanism, checkpoint and restoration semantics, optimizer reconciliation,
observability, and failure behavior through the native framework lifecycle.
Industry support does not introduce a separate enterprise training
implementation.

### M6.5 Performance and scale are characterized honestly

Measurements identify workload, hardware, topology, population, framework
versions, throughput, memory, checkpoint and storage cost, population overhead,
and recovery cost. Claims distinguish framework overhead, Clan algorithm cost,
and workload effects.

## Test and qualification gates

### M6.6 Every published support claim has direct qualification

Accelerator, topology, sharding, precision, optimizer, storage, recovery, and
observability tests jointly cover the configurations actually listed as
supported. Performance regression tests protect material operating costs.

### M6.7 Failure and restoration tests cover the accepted operational boundaries

Repeatable failure injection exercises the failure classes named by the support
matrix and verifies both machine behavior and operator-visible diagnosis.
Recovery evidence includes the state and lifecycle boundaries necessary to prove
that one coherent population resumes or that clean termination occurs.

## Documentation gates

### M6.8 Operations documentation enables independent deployment and recovery

The milestone delivers the support matrix, deployment and configuration guide,
storage and retention guidance, monitoring and record reference, recovery and
termination runbooks, symptom-oriented troubleshooting, performance and capacity
guidance, and framework-upgrade compatibility guidance.

### M6.9 Engineering and scientific claims remain honest

Design documents explain every remaining custom seam. Limitations, unsupported
configurations, operational costs, negative results, and unresolved risks appear
beside the claims they bound.

## Example and scientific-work gates

### M6.10 Scaled public workloads exercise the declared envelope

Public reproducible workloads cover serious accelerator training, each claimed
sharding mode, persistent checkpointing and restoration, observable lifecycle
records, and representative accepted failure handling through the same public
path users operate.

### M6.11 Scientific studies characterize value and limits at scale

Studies use the public package and declared support envelope, compare relevant
baselines, report compute, storage, and operational costs and confounders, and
publish favorable, neutral, or unfavorable outcomes with enough artifacts for
independent interpretation.

## Evidence and release gates

### M6.12 The industry-readiness audit covers the complete public path

The audit traces every support claim through implementation, qualification tests,
documentation, examples, records, and observed failure behavior. Private or
specially simplified paths do not establish support.

### M6.13 An independent team successfully operates the system

A team not responsible for implementation deploys a supported workload,
inspects a complete Clan lifecycle, diagnoses an accepted failure case, restores
or terminates according to the runbook, interprets performance and scientific
output, and identifies the support boundary. Any material documentation or
diagnostic gap blocks closure.

## Closure evidence

Milestone 6 closes only when the readiness audit, support matrix, accelerator and
sharding tests, failure and recovery evidence, performance and observability
results, operations documentation, scaled examples, scientific studies,
independent-team exercise, and human review agree on one support envelope.
