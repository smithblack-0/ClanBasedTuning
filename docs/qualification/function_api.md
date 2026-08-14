# Function API qualification

Status: qualified initial single-node CPU path
Date: 2026-08-14
Evidence: GitHub Actions run `31849703451`

## Qualified claim

The public Ray Tune function path repeatedly executes Clan generations with two concurrent
CPU members on one node, preserves explicit userspace genome application, and recovers the
same experiment through ordinary `Tuner.restore` after a deliberate post-restore failure.

This evidence applies to the corrected scheduler architecture that owns the synchronous Clan
transition instead of inheriting Ray PBT internals.

## Qualified environment

The real framework contract ran with:

- Python 3.11.15;
- Ray 2.57.0;
- Lightning 2.6.5;
- PyTorch 2.10.0+cpu;
- Linux;
- one CPU node; and
- two concurrently live Tune function trials/Clan members.

The dependency range is intentionally broader than this concrete evidence. Admitting a Ray
minor through package metadata is not itself a compatibility claim.

## Primary framework contract

`tests/framework_contracts/test_clan_function_api.py` uses real Ray, Lightning, PyTorch and
Tune checkpoint storage. The passing repeated-generation contract establishes that:

1. two Tune function trials join one Lightning/PyTorch DDP world;
2. training data remains partitioned and both ranks contribute to the shared training path;
3. Lightning-managed validation is complete/equivalent on both candidates;
4. userspace `on_train_start()` applies the current child genome after Lightning restores
   optimizer/training state;
5. member-local optimizer policy produces candidate divergence;
6. workers and scheduler agree on exactly one winner;
7. only the selected member persists/reports the Clan continuation while all ranks
   participate in Lightning checkpoint construction/barrier;
8. every next member inherits selected model state, optimizer momentum/history, and
   Lightning progress;
9. every next member—including the prior winner—receives an independent mutation of the
   same parent config in stable member order; and
10. Tune resumes every child from the selected checkpoint/config assigned by the owned
    scheduler transition.

For seed 7, when the first selected parent has `lr=0.2`, the two next learning rates are
approximately `0.1924690426284743` and `0.2159468026720305`.

## Interrupted experiment restoration

The restore contract waits until Lightning has restored a nonzero global step and entered
the user module's `on_train_start()`, writes an external marker proving that ordering, then
raises the intended failure. The test shuts down Ray, removes the failure condition, creates
a fresh Ray runtime, and restores through ordinary `Tuner.restore(..., resume_errored=True)`.

The passing contract establishes reconstruction of scheduler runtime actors and continuation
of both members without a second CBT restore API or user-created scheduler.

## Foundational topology contract

`tests/framework_contracts/test_tune_member_lightning_environment.py` also passed in the same
run. It establishes the logical one-process-node `TuneMemberEnvironment` and a real two-rank
GLOO DDP world in which independently launched Tune processes receive the same reduced
gradient/update through Lightning/PyTorch.

The explicit GLOO choice belongs to the CPU test harness. Production CBT does not select a
backend.

## Compatibility meaning

Ray 2.57.0 is directly qualified for this path. The package currently admits
`ray[tune]>=2.56,<3` to avoid needlessly breaking installations on every Ray minor release.
Future Ray changes that affect checkpoint/config transfer should first be handled in
`ray_compat.py` and requalified through this real lifecycle. Dependency bounds should narrow
only when a version is actually incompatible and no reasonable adapter repair exists.

## Non-claims

This qualification does not establish CUDA/NCCL, physical multi-node execution, atomic
cross-trial gang admission, active-collective participant recovery, arbitrary custom/sharded
checkpoint plugins, explicit distributed validation samplers, model-sharded Clan execution,
or realistic performance/overhead.
