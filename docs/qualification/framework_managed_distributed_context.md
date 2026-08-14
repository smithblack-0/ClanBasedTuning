# Framework-managed distributed-context qualification

Status: direct foundation evidence plus remaining support limits

## Purpose

This record captures the distributed foundation on which the complete function API is
built: separate Ray Tune trials can operate as stable Clan members/ranks in one
Lightning/PyTorch-managed DDP world without CBT creating another process group.

The later complete two-generation evidence is recorded separately in
[`function_api.md`](function_api.md). This document does not broaden that support claim.

## Qualified environment

The retained framework contract exercises:

- Ray 2.56.1;
- Lightning 2.6.5;
- PyTorch 2.10.0;
- Python 3.11;
- one CPU node;
- two concurrently live Ray Tune function trials;
- one externally launched Lightning process per trial; and
- one two-rank PyTorch DDP group spanning those processes.

The CPU harness uses GLOO through the normal Lightning/PyTorch setup. Production CBT code
does not select GLOO, call `torch.distributed.init_process_group`, call
`torch.distributed.destroy_process_group`, or create a Ray collective group for the Clan.

## Established identity and topology

The foundation proves that:

- one live Tune trial can represent one stable Clan member;
- one member process can represent one DDP global rank;
- stable member IDs 0 and 1 are explicitly assigned to ranks 0 and 1 rather than inferred
  from callback order;
- Lightning accepts the externally supplied rank, world size, and rendezvous facts; and
- the two independently launched Tune processes join one framework-managed DDP world.

The production runtime used by the complete function path now derives those assignments
from the complete set of Tune trial IDs and performs a per-invocation rendezvous rather
than relying on test-harness constants.

## Framework ownership

Source inspection and executable behavior establish that:

- Ray Tune creates and resources the trial processes;
- CBT supplies cohort identity and topology facts;
- Lightning/PyTorch initialize the distributed group;
- backend/device behavior belongs to the Lightning/PyTorch path;
- DDP owns gradient synchronization; and
- in the qualified externally launched topology, the process group remains active when
  ordinary `Trainer.fit()` returns and is ultimately released with the Tune trial process.

CBT does not compensate for that lifetime with package-owned process-group teardown.
Actor/process reuse is therefore not currently a support claim for the complete function
path.

## Shared-gradient evidence

The two-trial contract gives the ranks distinct local gradients and verifies that
Lightning/PyTorch reduce them to the same common gradient before the local optimizer
updates.

This establishes the key training seam needed by Clan Tuning: every member contributes to
shared gradient work while retaining a local optimizer update afterward.

The complete function qualification extends this foundation by showing member divergence,
population selection, checkpoint transition, and repeated operation.

## Population-operation ownership

The current complete path exchanges population fitness through
`trainer.strategy.all_gather()` on this already-established framework context. That
operation is qualified by [`function_api.md`](function_api.md), not by a separately owned
Ray/GLOO/NCCL population runtime.

No additional backend selection, rendezvous, or process-group lifecycle is introduced for
fitness exchange.

## What this foundation does not establish

The original two-rank environment contract does not by itself prove:

- complete Clan generation transitions;
- checkpoint selection or restore;
- userspace genome use;
- repeated generations;
- CUDA/NCCL;
- multi-node topology;
- actor reuse;
- bounded recovery after a member fails inside active distributed work;
- gang scheduling that prevents a partial cohort from temporarily holding resources;
- arbitrary validation-sampler arrangements; or
- ClanFSDP/model sharding.

Some of the complete-generation items are now established by
[`function_api.md`](function_api.md). The remaining items stay explicit non-claims until
directly qualified.

## Failure boundary

The current production runtime has a bounded pre-DDP rendezvous timeout if the complete
assigned cohort does not join. The qualification does not establish bounded release or
recovery after a participant disappears inside an active PyTorch collective.

That limitation is important: the architecture still forbids knowingly selecting from a
partial Clan, but the initial support claim does not promise that every distributed
failure mode is recovered without external framework/process failure handling.

## Evidence meaning

This record supports a narrow framework statement: independent Tune trial processes can be
wired into one Lightning/PyTorch-owned DDP context suitable for the initial Clan member
model, with shared gradients and no CBT-owned distributed backend.

Broader behavior is supported only where the corresponding complete-path qualification
records direct evidence.
