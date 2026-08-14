# Function API qualification

Status: direct evidence for the initial complete Clan Tuning path
Date: 2026-08-14

## Claim

The initial Ray Tune function-trainable integration completes two successive Clan
generations with two concurrently resident members on one CPU node while preserving the
accepted userspace genome boundary.

This qualification is intentionally narrow. It establishes the mechanics listed below for
the tested versions and topology; it does not imply adjacent GPU, multi-node, failure, or
explicit-user-sampler support.

## Qualified environment

The complete framework contract runs with:

- Python 3.11;
- Ray 2.56.1;
- Lightning 2.6.5;
- PyTorch 2.10.0;
- one machine;
- CPU execution;
- two concurrent Tune trials;
- one Lightning process/device per trial; and
- one two-rank PyTorch DDP world spanning the Clan.

The existing CPU harness reaches GLOO through the normal Lightning/PyTorch setup. CBT
production code does not select GLOO or any other process-group backend.

The dependency-light unit and repository-surface validation also runs on Python 3.13. The
complete Ray/Lightning contract is currently a Python 3.11 support claim.

## Executed contract

The evidence is `tests/framework_contracts/test_clan_function_api.py` together with the
previously qualified Tune-member DDP tests.

The end-to-end test uses a scalar Lightning model and SGD with momentum so inheritance and
member divergence are directly observable rather than inferred from opaque model state.

### 1. Ordinary Tune function configuration reaches userspace

Ray calls the wrapped function with a normal config dictionary containing the current
`lr` genome value.

The test's receiving function directly reads that dictionary. When a parent checkpoint is
present, test/userspace code:

1. materializes the Ray checkpoint locally;
2. loads the inherited optimizer state;
3. directly changes `optimizer.param_groups[*]["lr"]` from the received genome;
4. writes that changed optimizer state into its local Lightning checkpoint copy; and
5. passes that copy to ordinary `trainer.fit(..., ckpt_path=...)`.

No production CBT function performs, calls, wraps, or infers this application. Repository
surface tests explicitly reject production `apply_genome`, optimizer-param-group
application, and package-owned optimizer restore logic.

### 2. The Clan forms one framework-managed DDP world

Two Tune function trials become stable members/ranks 0 and 1 in one Lightning/PyTorch DDP
world through the externally assigned cluster environment.

The previously qualified environment contract verifies that distinct local gradients are
reduced to one common gradient by Lightning/PyTorch. No CBT process-group initialization,
backend selection, or second population group is used.

### 3. Training remains partitioned while validation is replicated

The end-to-end contract supplies four distinct training examples and four distinct
validation examples.

For training, Lightning's ordinary DDP sampler remains active. With one training batch per
round, the two final member reports contain two distinct training sample values. The exact
sample positions are intentionally not contracted because restored Lightning loop/sampler
progress determines where each rank resumes inside its shard.

For validation, `ClanDDPStrategy` changes only Lightning's automatically injected sampler
kwargs while the Trainer is validating or sanity checking. Every member receives an
effective one-replica sampler over the complete validation dataset.

The test enables Lightning's ordinary sanity validation, allowing the validation loader to
be prepared and cached through that normal path. At the real Clan validation boundary,
every member must report:

- validation sample count `4`; and
- validation sample sum `6` for examples `[0, 1, 2, 3]`.

Both members therefore evaluate the same complete held-out examples while training
remains partitioned.

Lightning does not automatically replace an explicitly user-supplied `DistributedSampler`.
CBT likewise leaves such a sampler untouched; its semantics are not established by this
qualification.

### 4. Member-local updates diverge after the common gradient

The initial genomes are `lr=0.1` and `lr=0.2`. Both members receive the same reduced
gradient, then apply their own optimizer configuration in ordinary Lightning/PyTorch
optimization.

The candidate with `lr=0.2` reaches weight `0.8` and wins the first minimizing
`weight**2` validation boundary over the `lr=0.1` member.

### 5. All members agree on one winner before Tune transition

At validation end, each member contributes one local scalar fitness through
`trainer.strategy.all_gather()` on the active Lightning strategy.

`ClanController` applies the shared deterministic selection policy locally. The Tune
scheduler independently applies the same policy to the complete results and rejects
worker/scheduler disagreement.

The test completes the boundary successfully with one common winner.

### 6. One persistent CBT continuation is produced

Every rank enters `Trainer.save_checkpoint()`, so Lightning constructs the required local
checkpoint state and executes its framework-owned post-save barrier.

`ClanDDPStrategy` delegates the scoped CBT checkpoint write to `CheckpointIO` only on the
selected rank. Losing ranks do not persist or report a CBT checkpoint.

The two-generation test asserts that persistent `checkpoint.ckpt` count is bounded by the
number of completed rounds rather than by population size times rounds.

This establishes the intended storage distinction:

> transient framework materialization is allowed; persistent Clan continuations remain
> winner-only.

### 7. Ray transfers the selected continuation to the next function invocation

The next generation receives the first winner's checkpoint through
`tune.get_checkpoint()`.

The strengthened full-restore contract verifies that both next members begin from:

- selected model weight `0.8`;
- inherited SGD momentum buffer `1.0`; and
- inherited Lightning `global_step == 1`.

Thus the generation transition preserves model state, optimizer history, and Lightning
training progress through the ordinary Lightning checkpoint restore path.

### 8. Every next member receives a sibling mutation of the selected parent genome

The scheduler snapshots the selected parent's `lr=0.2` config before mutating any target.
With mutation seed `7`, both next members receive independent mutations of that same
parent genome, including the preceding winner.

The test requires the two final configs to be approximately:

- `0.1924690426284743`; and
- `0.2159468026720305`.

This rejects stock-PBT semantics where the source member would retain its exact config,
and it rejects chained mutation where a later child would accidentally mutate an already
mutated sibling.

### 9. The supplied next genome is actually used by userspace

Each second-generation model logs the learning rate visible in its optimizer after the
user's restore/application block. The test requires that value to equal the corresponding
Ray result config.

This closes the public-path loop:

selected checkpoint + scheduler-produced child genome -> Ray function invocation ->
userspace genome use -> next Clan round.

## Current support limits

This qualification does not establish:

- CUDA/NCCL execution;
- multi-node execution;
- actor/process reuse across generations;
- recovery after a member disappears inside an active distributed collective;
- semantics of explicitly user-supplied distributed validation samplers;
- custom or sharded checkpoint plugins;
- model-sharded Clan execution / ClanFSDP; or
- scientific performance on realistic workloads.

The current runtime requires enough resources for the complete Clan to become resident
concurrently. It has a bounded pre-DDP rendezvous timeout but no CBT-specific cancellation
layer around an active framework collective.

The candidate fitness metric must remain member-local until CBT's population exchange;
logging it with cross-rank reduction would collapse the candidate distinction selection
needs.

Ray's stock PBT console logger currently reports no native hyperparameter mutations because
CBT's `MutationSpec` policy intentionally does not populate Ray's built-in mutation table.
The resulting child configs are directly asserted by the contract; richer mutation
observability is follow-up work rather than part of this support claim.

## Acceptance meaning

This record supports one claim: the initial two-member single-node CPU function API is a
real repeated Clan Tuning mechanics path, not an isolated callback or synthetic state
transfer.

Broader support requires direct qualification of the broader configuration. Future work
must extend the same public path and preserve the same ownership boundary: CBT supplies a
genome; user code owns what it means and what it does.
