# Function API qualification

Status: qualification target after scheduler correction
Date: 2026-08-14

## Claim under test

The public Ray Tune function path must repeatedly execute Clan generations with two
concurrent CPU members on one node, preserve explicit userspace genome application, and
recover the same experiment through ordinary `Tuner.restore` after a deliberate post-restore
failure.

Because the corrective branch replaces PBT inheritance with an owned scheduler transition,
previous mechanics evidence is not automatically carried forward. The claim becomes current
qualification only when the exact corrective branch head passes the real framework contract.

## Primary framework contract

`tests/framework_contracts/test_clan_function_api.py` uses real Ray, Lightning, PyTorch and
Tune checkpoint storage. It must establish:

1. two Tune function trials join one Lightning/PyTorch DDP world;
2. training data remains partitioned and both ranks contribute to a common reduced gradient;
3. Lightning-managed validation is complete/equivalent on both candidates;
4. userspace `on_train_start()` applies the current child genome after Lightning restores
   optimizer/training state;
5. member-local optimizer policy produces candidate divergence;
6. all workers and the scheduler agree on exactly one winner;
7. only the selected member persists/reports the Clan continuation while all ranks
   participate in Lightning checkpoint construction/barrier;
8. every next member inherits selected model state, optimizer momentum/history, and
   Lightning progress;
9. every next member—including the prior winner—receives an independent mutation of the
   same parent config in stable member order; and
10. Tune resumes every child from the selected checkpoint/config assigned by the owned
    scheduler transition.

For seed 7, when the first selected parent has `lr=0.2`, the two next learning rates are
required to be approximately `0.1924690426284743` and `0.2159468026720305`.

## Interrupted experiment restoration

The restore contract deliberately waits until Lightning has restored a nonzero global step
and entered the user module's `on_train_start()`, records an external marker proving that
ordering, then raises the intended failure. The test shuts down Ray, removes the failure
condition, creates a fresh Ray runtime, and calls:

```python
Tune.Tuner.restore(..., trainable=..., resume_errored=True)
```

Successful completion must reconstruct the scheduler's runtime registry/coordinator and
continue both members without rebuilding a CBT scheduler in user code.

The test catches the expected Tune-level experiment error only; an unrelated arbitrary
exception must not silently satisfy the intentional-failure phase.

## Foundational topology contract

`tests/framework_contracts/test_tune_member_lightning_environment.py` separately proves the
externally launched Lightning seam. Two Tune trials use the logical one-process-node
`TuneMemberEnvironment`, form one native GLOO DDP group, and observe the same reduced
gradient/final parameter update.

The explicit GLOO choice belongs to the CPU test harness. Production CBT does not choose a
backend.

## Compatibility meaning

The package dependency range is intentionally broader than this exact qualification
configuration. Passing on one Ray version establishes support for that version, not for every
minor admitted by dependency metadata. As compatibility coverage expands, CI/tests should run
representative Ray versions rather than solving maintenance by point-pinning users.

A failure caused by Tune internal checkpoint/config transfer should first be repaired in
`ray_compat.py`; only an irreconcilable upstream change warrants narrowing dependency bounds.

## Non-claims

This qualification does not establish CUDA/NCCL, physical multi-node execution, insufficient
cluster-capacity admission semantics beyond bounded rendezvous failure, active-collective
participant recovery, arbitrary custom/sharded checkpoint plugins, explicit distributed
validation samplers, model-sharded Clan execution, or realistic performance/overhead.
