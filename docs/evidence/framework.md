# Framework evidence

Status: active version-sensitive evidence  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

This file preserves upstream observations and open qualification questions used by the active architecture and contracts. It is evidence, not product authority, an implementation plan, or a compatibility promise.

## Ray population and trial lifecycle

### Trial population and residency

Ray's `BasicVariantGenerator` generates trials from `num_samples` and search-space expansion. Tune's controller separately manages actor staging and resources.

Consequences:

- Clan membership must correspond to the actual live Tune trial set rather than an independent package-owned population count.
- Scheduler policy alone does not prove complete concurrent residency.
- The integration must verify that trial generation, resource capacity, collective membership, and the configured Clan describe one live population before shared-gradient work begins.

Sources:

- Ray `BasicVariantGenerator`, revision `27b0e6a7b88324eab5214a0bc65a839bfbb2dc85`
- Ray `TuneController`, same revision

Open qualification: identify the native Ray signals sufficient for reliable complete-population preflight.

### Tune function checkpoint flow

Ray's Lightning integration can attach a Lightning checkpoint to `tune.report()`. Function-trial restoration exposes an assigned checkpoint through `tune.get_checkpoint()`. Tune separates result handling, checkpoint state, pausing, and restoration.

Consequences:

- CBT does not need a package-owned `Trainable` or second checkpoint format.
- Winner-only reporting and common next-generation restoration must be qualified against the pinned Ray function path.
- The CBT scheduler may reuse native trial/config/checkpoint assignment but must not delegate Clan winner policy to ordinary PBT quantile logic.

Sources:

- Ray Lightning report/checkpoint integration
- Ray `FunctionTrainable`
- Ray synchronous PBT and Tune controller source, revision above

Open qualification: prove the narrow scheduler seam for complete-generation verification, target configuration replacement, common checkpoint assignment, persistence, and recovery.

### Experiment restoration

`Tuner.restore` and Tune persistent storage provide native experiment-level restoration mechanisms.

Consequence: native recovery must be qualified before introducing a Clan-specific generation manifest or transaction system. Ordinary generation continuation and industry-grade interruption recovery are separate support questions.

## Ray collective communication

Ray 2.56 exposes collective groups and all-gather for supported CPU/GLOO and GPU/NCCL paths.

Consequences:

- The initial population runtime can use one all-gather to obtain complete population fitness while leaving winner policy in the shared framework-independent selector.
- Stable member identity must be explicitly associated with collective participation; incidental buffer position is insufficient without a proven mapping.
- CPU evidence does not establish CUDA/NCCL support, and documentation alone does not establish executable behavior.

Open qualification:

- group construction and teardown across the live Tune population;
- failure and timeout release;
- generation isolation across repeated operations;
- identity preservation under participant reordering; and
- transport precision sufficient to preserve selection.

## Lightning training and checkpoint boundaries

### Validation cadence

Lightning owns validation timing through Trainer configuration, including epoch, subepoch, and time-based forms.

Consequences:

- CBT should consume a qualifying Lightning event rather than maintain another progress clock.
- Time-based validation is unsafe to claim without evidence that all members reach the same collective boundary despite runtime jitter.

Open qualification: determine the supported validation, accumulation, loader, and continuation configurations for one coherent generation boundary.

### Checkpoint construction and persistence

Lightning owns checkpoint payload construction, optimizer and progress restoration, strategy barriers, and persistence hooks. Ordinary DDP strategies may assume equivalent replicas when gating writes.

Consequences:

- Every required rank must participate in the Lightning checkpoint boundary.
- The integration must expose one persistent checkpoint from the selected divergent member without inventing a second checkpoint system.
- Winner-side Ray metadata annotation must not deserialize or modify the Lightning payload.

Open qualification: identify and prove the narrowest Lightning seam for selected-member persistence across the intended launch topology.

### Optimizer restoration ordering

Lightning restores optimizer state through the strategy/checkpoint connector before later user or integration logic reapplies controlled values.

Consequence: the receiving member's evolved optimizer genome must be applied after inherited optimizer history is restored. Competing learning-rate schedulers or hooks that rewrite the same fields require an explicit supported contract.

## PyTorch DDP

PyTorch DDP owns parameter verification, initial synchronization, gradient hooks, bucketing, and reduction.

Focused evidence established that native DDP can:

- synchronize the initial model state;
- preserve equal reduced gradients;
- disable forward-time persistent-buffer broadcast where necessary; and
- allow different local optimizer values to produce divergent parameters after the shared gradient.

Consequences:

- CBT should configure or narrowly specialize DDP rather than reimplement gradient reduction.
- Optimizer history and genome remain local; only the gradient is shared.
- The integration must prove that no later framework behavior erases intended member divergence.

Open qualification: define the supported precision, accumulation, buffer, model, and loader configurations. Later sharding support requires separate native-strategy evidence.

Source revision: PyTorch `4899d123e80a124f31e45ed832bba195af32c353`.

## Fitness comparability

Clan selection requires candidate fitness from equivalent held-out work at the same logical boundary. DDP-reducing the candidate scores would erase the differences being compared.

Standard PyTorch sampling can provide equivalent deterministic evaluation data without a package-owned data framework.

Open qualification: sampler, transforms, ordering, loader length, metric behavior, and reporting path for the supported integration.

## Collective failure and stopping

Tune ordinarily evaluates per-trial stop and failure behavior in trial lifecycle order. Independent stopping or recovery can remove a member from the fixed population before the Clan transition completes.

Consequences:

- member-local early stopping cannot silently govern a Clan generation;
- one failed required member invalidates both the DDP world and the population that produced the shared gradient; and
- no supported path continues with a reduced population.

Open qualification: prove bounded failure release for collective waiters and coherent scheduler invalidation without partial next-generation release.

## Evidence limits

The source observations above justify architecture and targeted qualification work. They do not prove the current package implements those paths or establish support beyond directly executed tests.

Each support claim records the exact framework versions, backend, device, topology, resource assignment, failure configuration, and retained test output that establish it.

## Source revisions

- PyTorch: `4899d123e80a124f31e45ed832bba195af32c353`
- Lightning: `7f0c3436cd3f6ad3753125672024fc415cbcb414`
- Ray: `27b0e6a7b88324eab5214a0bc65a839bfbb2dc85`
