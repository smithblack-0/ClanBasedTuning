# Framework-managed distributed-context qualification

Status: qualified single-node CPU foundation
Date: 2026-08-14
Evidence: GitHub Actions run `31849703451`

## Purpose

This record captures the distributed foundation used by the complete function API: separate
Ray Tune trials can operate as stable Clan members/ranks in one Lightning/PyTorch-managed DDP
world without CBT creating another process group.

## Qualified environment

The current retained framework contract passed with:

- Ray 2.57.0;
- Lightning 2.6.5;
- PyTorch 2.10.0+cpu;
- Python 3.11.15;
- Linux;
- one CPU node;
- two concurrently live Ray Tune function trials; and
- one externally launched Lightning process per trial.

The CPU harness chooses GLOO through the normal Lightning/PyTorch setup. Production CBT code
does not select GLOO, initialize/destroy the process group, or create a second Ray collective
group.

## Established identity and topology

The passing contract establishes that one live Tune trial can represent one stable Clan
member and one DDP global rank. Each Tune process has local rank zero and is presented as one
logical one-process Lightning node, with logical node/global rank equal to stable member ID.
That representation is adapter bookkeeping rather than physical machine identity.

The production runtime derives assignments from the complete Tune trial set and uses a fresh
per-invocation rendezvous rather than test-harness constants.

## Framework ownership

The evidence establishes that:

- Ray Tune creates and resources trial processes;
- CBT supplies cohort identity and topology facts;
- Lightning/PyTorch initialize the distributed group;
- backend/device behavior belongs to Lightning/PyTorch;
- DDP owns gradient synchronization; and
- CBT does not compensate with package-owned process-group lifecycle machinery.

## Shared-gradient evidence

The two-trial contract gives ranks distinct local gradients and verifies that
Lightning/PyTorch reduce them to the same common gradient before local optimizer updates.
This is the required Clan training seam: every member contributes to shared gradient work
while retaining its own post-gradient optimizer update.

The complete function qualification separately establishes divergence, selection, checkpoint
transition, sibling mutation, repeated operation, and fresh-runtime restore.

## Support boundary

This foundation does not establish CUDA/NCCL, physical multi-node topology, actor reuse,
bounded recovery after a member fails inside active distributed work, atomic cross-trial gang
scheduling, arbitrary validation-sampler arrangements, or model-sharded Clan execution.

The current runtime has a bounded pre-DDP rendezvous timeout and the scheduler forbids an
early-paused member from entering the next generation until the complete current boundary has
resolved. The entire Clan must nevertheless fit concurrently on provisioned resources.
