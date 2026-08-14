# Function API qualification

Status: exact-head qualification target for the productized function path
Date: 2026-08-14

## Claim under test

The public Ray Tune function integration should complete repeated Clan generations with two
concurrent CPU members on one node, preserve the userspace genome boundary, and recover the
same experiment through Ray's ordinary `Tuner.restore` interface after a deliberate
post-checkpoint interruption.

This record is intentionally narrow. It does not imply GPU, multi-node, active-collective
failure recovery, custom checkpoint-plugin, or model-sharded support.

## Environment

The complete framework contract targets:

- Python 3.11;
- Ray 2.56.1;
- Lightning 2.6.5;
- PyTorch 2.10.0;
- Linux CI;
- one machine;
- CPU execution;
- two concurrent Tune trials; and
- one Lightning process/device per trial.

Dependency-light checks also run on Python 3.13.

## Executed contracts

`tests/framework_contracts/test_clan_function_api.py` is the complete lifecycle evidence;
`test_tune_member_lightning_environment.py` separately qualifies the underlying two-trial
DDP seam.

The complete contract is designed to establish:

1. Ordinary Tune config reaches userspace unchanged; the test directly edits optimizer
   param groups from that config rather than calling a CBT application helper.
2. Two Tune trials form one Lightning/PyTorch-managed DDP world and receive a common reduced
   gradient.
3. Training remains rank-partitioned while Lightning-managed validation is replicated so
   both candidates evaluate the same complete held-out examples.
4. Different member-local optimizer policy creates divergence after the common gradient.
5. All members and the scheduler agree on exactly one winner.
6. Every rank participates in Lightning checkpoint construction/barrier but only the winner
   persists/reports the Clan continuation.
7. Ray transfers the selected model/optimizer/Lightning progress to the next generation.
8. Every next member, including the prior winner, receives an independent sibling mutation
   of the same selected parent Tune config.
9. Userspace actually observes/applies the newly assigned config after restoration.

For the scalar contract, the first winner is the `lr=0.2` candidate at model weight `0.8`.
The next generation must inherit model weight `0.8`, SGD momentum buffer `1.0`, and
Lightning `global_step == 1`. With mutation seed 7, the two sibling learning rates must be
approximately `0.1924690426284743` and `0.2159468026720305`.

## Interrupted-experiment restoration

A separate end-to-end test distinguishes ordinary generation transition from durable Tune
experiment recovery:

1. run the same two-member Clan until a successful selected continuation exists;
2. deliberately fail the next receiving invocation after it sees that checkpoint;
3. shut down the Ray runtime;
4. confirm the Tune experiment directory is restorable;
5. remove the deliberate failure condition;
6. start a fresh Ray runtime;
7. call `Tuner.restore(experiment_path, trainable=..., resume_errored=True)` without
   reconstructing or wrapping a `ClanScheduler`; and
8. require both members to continue successfully through later training iterations while
   still seeing their current Tune config in userspace.

This specifically qualifies the internal runtime registry/coordinator reconstruction from
restored scheduler state. A within-run PBT checkpoint transition is not accepted as a
substitute for this evidence.

## API/readiness properties exercised

The productized path also removes several previous usability-only seams:

- no `ClanScheduler.wrap(train)` public operation;
- metric/mode supplied once through `TuneConfig`;
- no user-facing `MutationSpec` object;
- no required `Trainer(devices=1)` duplication; and
- no example helper that hides userspace genome application.

These are API properties, while the framework tests establish their executable consequences.

## Support limits

This qualification does not establish CUDA/NCCL, multi-node execution, actor reuse,
bounded recovery after a member disappears inside an active distributed collective,
explicit user-distributed-validation-sampler semantics, custom/sharded checkpoint plugins,
ClanFSDP/model sharding, or realistic scientific performance/overhead.

The complete population must still be schedulable concurrently. The current runtime has a
bounded pre-DDP rendezvous timeout but no CBT-specific watchdog around an active framework
collective.

## Acceptance rule

This document is only a direct qualification once the exact branch head containing these
contracts passes the repository's Ray framework-contract job. If exact-head CI is not
green, treat the claim above as a qualification target rather than established support.
