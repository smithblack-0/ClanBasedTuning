# Current integration design

Status: implemented design for the initial Ray Tune function path

## Purpose

This document defines the current system lifecycle, state authorities, and framework
boundaries. It does not redefine the Clan Tuning method or duplicate the public usage
example in [`../api.md`](../api.md).

The design is firm where implementation and direct framework evidence have selected a
working path. Unqualified hardware, failure, explicit-sampler, and model-sharding
extensions remain open rather than being implied by the initial CPU evidence.

## Runtime model

One live Ray Tune function trial represents one stable Clan member. In the initial DDP
path, that trial contains one externally launched Lightning process and one rank in the
DDP world spanning the complete Clan.

`ClanScheduler` is the Tune-side evolutionary authority. It specializes Ray's synchronous
Population Based Training lifecycle so Ray still owns trial execution, pausing, checkpoint
transfer, restart, and config replacement while CBT supplies the single-parent Clan
policy.

`ClanScheduler.wrap(train)` carries hidden stable-member and rendezvous context beside the
user function. The dictionary passed to `train(genome)` remains Ray's ordinary Tune
configuration. The wrapper does not inspect or rewrite it.

The initial path requires the complete population to be resident concurrently. A member
that reaches the wrapper before the complete cohort assignment waits for the remaining
members. Insufficient cluster capacity is therefore an unsupported configuration rather
than a population that may be time-multiplexed safely.

## Genome ownership

The CBT scheduler owns selection and mutation of Tune config values. It does not own what
those values mean inside the user's program.

The current genome is passed unchanged to the user's function. User code alone decides
whether a key controls an optimizer, another piece of state, or nothing at all. CBT has no
optimizer schema, genome-application function, application callback, restore hook, or
post-load application hook.

For scientifically faithful Clan Tuning experiments, the varied choices must remain
compatible with the shared-gradient method described by the roadmap. That scientific
constraint does not become a library-owned application mechanism.

## Distributed training lifecycle

`ClanDDPStrategy` is a Lightning `DDPStrategy` supplied with the stable rank, world size,
and rendezvous facts assigned to the Tune-member cohort.

Lightning and PyTorch own:

- accelerator and backend selection;
- process-group initialization;
- DDP model setup;
- gradient collectives;
- barriers and other distributed operations;
- training and validation loop execution; and
- process-group lifetime within the qualified externally launched trial lifecycle.

CBT does not establish a second process group for population resolution and does not
hardcode GLOO, NCCL, CPU, CUDA, or another backend. The CPU qualification harness reaches
GLOO through Lightning/PyTorch's ordinary setup.

The strategy disables DDP per-forward buffer broadcast after setup. This prevents later
member-local persistent buffers from being silently replaced by rank-zero values after the
members have diverged.

For Lightning-managed dataloaders, training keeps ordinary DDP partitioning. Validation
has a different Clan requirement: every diverged candidate must be scored on the same
held-out examples. When Lightning would automatically inject a `DistributedSampler` for
validation or sanity validation, `ClanDDPStrategy` supplies sampler kwargs equivalent to a
single replica (`num_replicas=1, rank=0`) on every member. Each member therefore evaluates
the complete validation dataset while training remains partitioned.

Lightning only performs that automatic replacement when the user has not already supplied
a `DistributedSampler`. An explicitly supplied distributed sampler remains userspace and
CBT does not replace or reinterpret it.

## Round boundary and member-local fitness

A round closes at Lightning validation end through `ClanTuneReportCallback`. Lightning's
validation cadence therefore defines round cadence; CBT does not maintain a second
training-progress counter.

Each member supplies one local fitness metric at the same logical boundary. The callback
passes that scalar to `ClanController`. The controller's injected exchange uses
`trainer.strategy.all_gather`, so fitness travels over the already-established
Lightning/PyTorch distributed context.

Every member applies the same framework-independent selection function to the complete
fitness vector and reaches the same winner identity before reporting to Tune. The
scheduler independently repeats the selection from the complete Tune results and rejects
a disagreement.

The fitness metric must remain member-local until CBT compares it. User logging that
reduces the candidate fitness across ranks would destroy the distinction CBT needs.

The qualified default Lightning data path verifies both sides of the intended sampling
behavior with a multi-example dataset: the two training members consume distinct shard
samples, while both validation members see all four held-out examples (count `4`, sum
`6`), including when Lightning first prepares the validation loader for its normal sanity
check.

## One selected continuation

At the round boundary, every rank calls ordinary `Trainer.save_checkpoint()`. This is
necessary because Lightning's distributed checkpoint boundary includes a post-save
barrier.

`ClanDDPStrategy` scopes that CBT round save to one selected writer. Every member builds
whatever transient checkpoint state Lightning requires, but only the winner delegates the
checkpoint to the configured `CheckpointIO`. The winner alone turns that temporary
checkpoint into a Ray Tune checkpoint and reports it.

The scheduler verifies the reported stable member identity, independently verifies the
winner, and verifies that exactly that member declared itself the checkpoint source. Ray's
PBT checkpoint machinery then obtains the checkpoint from that selected source trial.

No checkpoint-embedded genome copy is required by the implemented path. The selected
checkpoint source and the selected parent Tune config are both already known to the
scheduler at the accepted boundary. CBT does not duplicate the genome inside the
Lightning payload merely to recover information the scheduler already owns.

Persistent CBT continuation storage therefore scales as one checkpoint per completed
round, not one checkpoint per Clan member. Temporary framework materialization and Ray's
normal checkpoint transport are not additional Clan continuations.

## Full continuation restore and userspace application

For a resumed member, Ray exposes the selected parent checkpoint through
`tune.get_checkpoint()` and supplies that member's newly assigned genome as the function
argument.

The qualified Lightning pattern is:

1. user code materializes its received checkpoint locally;
2. user code restores whatever inherited state it needs in order to apply the current
   genome;
3. user code applies the genome by whatever logic it chooses;
4. user code writes those changes into its local checkpoint copy if Lightning's later
   full restore would otherwise overwrite them; and
5. ordinary `trainer.fit(..., ckpt_path=local_checkpoint)` restores the complete selected
   Lightning continuation.

The real contract verifies inherited model state, optimizer momentum, and Lightning
`global_step` across the generation transition. The genome-use operation in that test is
written directly in the test function as userspace code. CBT does not call it or provide
an equivalent production helper.

## Scheduler-owned generation transition

When all member reports reach a synchronous PBT boundary, `ClanScheduler`:

1. verifies one report for every assigned stable member;
2. verifies that all reports belong to one Tune training iteration;
3. independently selects the winner from the complete fitness vector;
4. checks worker/scheduler winner agreement and the single checkpoint-source declaration;
5. snapshots the selected parent's current Tune config;
6. lets Ray retain that selected trial's checkpoint as the common continuation;
7. gives every next member, including the selected member, an independent mutation of the
   same snapshotted parent config; and
8. relies on Ray's synchronous pause/checkpoint/config/restart lifecycle to transfer the
   accepted transition.

All child mutations are therefore siblings of the same selected parent genome. The
winning member is not exempt from mutation.

The scheduler owns its mutation random stream. It does not own user optimizer state or
interpret the mutated keys.

## Responsibility boundaries

- **Ray Tune** owns trials, resources, scheduler lifecycle, pause/restart behavior, and
  native checkpoint/config transfer.
- **`ClanScheduler`** owns stable Clan membership, one-parent selection verification,
  mutation, and assignment of next Tune configs.
- **The hidden worker runtime** owns only cohort identity and rendezvous facts needed to
  connect separate Tune trials into the qualified externally launched Lightning world.
- **Lightning/PyTorch** own distributed initialization, backend/device behavior, DDP,
  gradients, collectives, training/validation cadence, full-state restoration, checkpoint
  construction, and checkpoint barriers.
- **`ClanDDPStrategy`** supplies the Clan topology, preserves training partitioning, and
  adapts only Lightning's automatically managed validation sampler to replicate the
  held-out set across candidates.
- **`ClanTuneReportCallback`** bridges one Lightning validation boundary to one Tune
  report and winner-only CBT checkpoint.
- **`ClanController`** owns one local fitness, one complete-population decision, and the
  cached selected-member answer.
- **User code** owns the genome's meaning and every effect it has on model, optimizer, or
  other program state; explicit user-supplied distributed samplers are likewise not
  rewritten by CBT.

The integration contains no package-owned Trainer, Trainable subclass, replacement
training loop, second process group, second checkpoint payload, or CBT-owned genome
application system.

## Current qualification boundary

The complete path is directly qualified for two concurrent members on one CPU node with
Ray 2.56.1, Lightning 2.6.5, PyTorch 2.10.0, and Python 3.11. The test covers two
successive generations through the real public function path and the ordinary
Lightning-managed training/validation sampler path.

The current evidence does not establish:

- CUDA/NCCL behavior;
- multi-node execution;
- actor reuse;
- failure recovery or bounded release after a failed collective participant;
- semantics of explicitly user-supplied distributed validation samplers;
- custom/sharded checkpoint plugins; or
- ClanFSDP/model-sharded execution.

Those are support extensions or hardening work. They must extend this public path rather
than replace it with another training or application system.
