# Function API qualification

Status: corrected CPU function path directly qualified
Date: 2026-08-14

## Current evidence

The executable readiness/audit candidate is commit
`8f4e07ea93c8d4525920212f93c365cfd148e1e7`. GitHub Actions run `31852871160` passed the real
Ray/Lightning contract set on Python 3.11.15 with Ray 2.57.0, Lightning 2.6.5, PyTorch
2.10.0+cpu, Linux, and local CPU execution.

The same exact commit passed ordinary validation on Python 3.11 and 3.13, including Ruff,
package-source mypy, distribution build/rendering, non-editable wheel import, and pure unit
contracts.

## Repeated full-state contract

`tests/framework_contracts/test_clan_function_api.py` uses real Ray, Lightning, PyTorch and
Tune checkpoint storage. It establishes that:

1. two Tune function trials join one Lightning/PyTorch DDP world;
2. training data remains partitioned and both ranks contribute to a common reduced gradient;
3. Lightning-managed validation is complete/equivalent on both candidates;
4. userspace `on_train_start()` applies the current child genome after Lightning restores
   optimizer/training state;
5. member-local optimizer policy produces candidate divergence;
6. all workers and the scheduler agree on exactly one winner;
7. only the selected member persists/reports the Clan continuation while all ranks participate
   in Lightning checkpoint construction/barrier;
8. every next member inherits selected model state, optimizer momentum/history, and Lightning
   progress;
9. every next member—including the prior winner—receives an independent mutation of the same
   parent config in stable member order; and
10. Tune resumes every child from the selected checkpoint/config assigned by the owned
    scheduler transition.

For seed 7, when the first selected parent has `lr=0.2`, the two next learning rates remain
approximately `0.1924690426284743` and `0.2159468026720305`.

## Realistic small-workload contract

`tests/framework_contracts/test_tiny_mlp_function_path.py` supplements the scalar mechanics
contract with a two-layer regression MLP, AdamW, fixed synthetic data, ordinary
forward/loss/backward, two training batches per invocation, optimizer-state restoration, and
userspace application of child learning-rate/weight-decay values.

This contract is intentionally small enough for repository qualification. It does not require
a model download or pretend that a tiny synthetic workload establishes realistic production
throughput.

## Interrupted experiment restoration

The restore contract deliberately waits until Lightning has restored a nonzero global step
and entered the user module's `on_train_start()`, records an external marker proving that
ordering, then raises the intended failure. The test shuts down Ray, removes the failure
condition, creates a fresh Ray runtime, and calls ordinary `Tuner.restore(...,
resume_errored=True)`.

Successful completion reconstructs the scheduler's registry/coordinator and continues both
members without a CBT-specific restore API or user-rebuilt scheduler.

## Insufficient-capacity failure boundary

`tests/framework_contracts/test_failure_boundaries.py` gives Ray one CPU while configuring a
two-member Clan. Both Tune trials must fail at the CBT complete-cohort rendezvous boundary
before DDP initialization. The test rejects a later `DistNetworkError`, protecting against a
stale timed-out member being reused as a dead rendezvous peer.

The coordinator retracts the exact timed-out pre-DDP announcement before the process raises.
This makes the configured Clan rendezvous timeout the product failure boundary; overall GitHub
worker/process startup latency is deliberately not treated as a product timing SLO.

## Foundational topology contract

`tests/framework_contracts/test_tune_member_lightning_environment.py` separately proves the
externally launched Lightning seam. Two Tune trials use the logical one-process-node
`TuneMemberEnvironment`, form one native GLOO DDP group, and observe the same reduced
gradient/final parameter update.

The explicit GLOO choice belongs to the CPU test harness. Production CBT does not choose a
backend.

## Runtime lifecycle

Scheduler-owned runtime construction is delegated to injected functions in the runtime
construction layer. Registration is performed once per live scheduler process instead of on
every scheduling callback. After every member of a successful population completes, the
experiment-scoped registry entries are removed and the cohort-specific coordinator actor is
terminated. Live handles are excluded from scheduler serialization so restore can reconstruct
them.

Errored experiments retain the assignment needed for Tune retry/restore semantics; CBT does
not silently convert Ray failure policy into its own process supervisor.

## Compatibility meaning

The package dependency range is intentionally broader than this exact qualification
configuration. Passing on Ray 2.57.0 establishes direct support evidence for Ray 2.57.0, not
for every minor admitted by metadata. Compatibility expansion should come from representative
framework contracts rather than point-pinning users.

A failure caused by Tune internal checkpoint/config transfer should first be repaired in
`ray_compat.py`; only an irreconcilable upstream change warrants narrowing dependency bounds.

## Non-claims

This qualification does not establish CUDA/NCCL, physical multi-node execution, transparent
recovery after losing a participant inside an active collective, arbitrary custom/sharded
checkpoint plugins, explicit user-supplied distributed validation samplers, model-sharded
Clan execution, or representative production performance/overhead.
