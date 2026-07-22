# Lightning component and lifecycle contracts

Status: superseded historical design detail; see `native_trial_build_contract.md`

Date: 2026-07-21

## 6. Recommended object contracts

### 6.1 `ClanScheduler`

This is the product's primary algorithmic object.

Its main idea is:

> Given a completed generation's member records, decide the source lineage and the next optimizer configurations.

It owns:

- fitness direction and ranking policy;
- elite/source selection;
- mutation policy;
- initialization of the first member configurations;
- policy RNG and reproducibility;
- lineage records;
- generation number and next expected boundary;
- serialization and replay information.

It explicitly does **not** own:

- Lightning objects;
- optimizers or model tensors;
- process groups;
- files or checkpoint storage;
- dataloaders;
- logging backends.

Suggested conceptual interface:

```python
class ClanScheduler(Protocol):
    def initialize(self, request: InitializationRequest) -> InitializationPlan: ...
    def propose(self, snapshot: GenerationSnapshot) -> GenerationPlan: ...
    def commit(self, plan: GenerationPlan) -> None: ...
    def state_dict(self) -> dict[str, object]: ...
    def load_state_dict(self, state: Mapping[str, object]) -> None: ...
```

`GenerationSnapshot` should be immutable and contain only scheduler-relevant information: generation, global optimizer step, member IDs, fitness, current genomes, and lineage IDs.

`GenerationPlan` should be immutable and include:

- plan ID;
- source member;
- target genome for each rank slot;
- elite designation;
- mutation operation records;
- parent/child lineage IDs;
- enough information for deterministic audit and replay.

The plan should be committed only after the distributed transition succeeds. If transfer fails, the job should crash and recover from the previous authoritative checkpoint rather than repair partially transferred state.

The first built-in policy should be a synchronous champion-centered scheduler:

- choose the best member;
- retain one exact elite configuration;
- create local mutations around the champion for the other member slots;
- reseed every model and optimizer state from the champion.

Alternative controllers can be added later without changing the Lightning integration.

### 6.2 `ClanTuningCallback`

Its main idea is:

> Translate Lightning lifecycle events into one transactional clan-generation transition.

Responsibilities:

- initialize or restore scheduler state at `on_train_start`;
- identify completed optimizer-step boundaries;
- ignore sanity-check validation;
- obtain the local member fitness;
- gather member records;
- invoke `scheduler.propose()` only on global rank 0;
- broadcast the small `GenerationPlan` object;
- ask the strategy to transfer source state;
- apply target optimizer genomes through bindings;
- clear pending gradients;
- barrier and verify transition completion;
- call `scheduler.commit()` on rank 0;
- synchronize committed scheduler metadata;
- emit generation metrics and lineage;
- optionally request a durable clan checkpoint.

It explicitly does not implement mutation algebra or large tensor movement.

`on_train_start`, not `on_fit_start`, is the correct activation hook. With the required delayed checkpoint restore, `on_fit_start` occurs before optimizer restoration and any mutations performed there would be overwritten on resume.

`on_validation_end` is the leading generation-transition hook because:

- epoch metrics have been finalized;
- local callback metrics still exist;
- ModelCheckpoint callbacks are reordered to run last;
- validation ends before the next training batch.

The callback must key its own boundary state to `trainer.global_step`, not to epoch count.

### 6.3 `ClanDDPStrategy`

Its main idea is:

> Make intentionally divergent DDP replicas a correct Lightning execution and persistence mode.

Required behavior:

1. subclass `DDPStrategy`;
2. enforce `broadcast_buffers=False`;
3. retain `init_sync=True` for structural verification and initial cloning;
4. reject model averaging/post-local-SGD modes;
5. expose efficient source-rank state transfer;
6. return `restore_checkpoint_after_setup=True`;
7. save a rank-local Lightning checkpoint shard from every rank;
8. write and validate a rank-0 manifest;
9. load the shard corresponding to the current logical member slot;
10. validate fixed world size and checkpoint format on resume.

A contract probe implemented the minimal save/load overrides and confirmed that Lightning restored divergent model weights and optimizer learning rates correctly on both ranks after DDP setup.

The strategy should not contain selection or mutation logic.

### 6.4 Tensor state transfer

Large state should not use `broadcast_object_list`. Pickling a model-sized optimizer state through object collectives would stage tensors through CPU memory and make generation boundaries unnecessarily expensive.

The leading implementation is a chunked tensor-tree broadcaster using public tensor collectives:

- transfer small tree/schema metadata as an object;
- group tensor leaves by device and dtype;
- flatten into bounded-size contiguous buckets;
- broadcast each bucket from the selected source rank;
- reconstruct or copy tensor leaves on every destination;
- load reconstructed optimizer state through `optimizer.load_state_dict()`.

Transfer products:

- every model parameter;
- every registered buffer, including nonpersistent buffers unless explicitly excluded;
- optimizer tensor and scalar state;
- optimizer param-group metadata before applying the next genome;
- later, supported scheduler or precision state where the contract requires it.

Do not clone RNG or dataloader position during ordinary exploit. Each rank should continue producing separate data and stochastic augmentation streams. Durable checkpoint recovery is a separate concern.

A simpler per-tensor broadcast is acceptable as the first correct implementation, with bucketed transfer introduced before performance claims. Disk checkpoint reload should remain a fallback/debug transfer backend, not the normal generation path.

### 6.5 Optimizer binding layer

Automatic arbitrary mutation of any optimizer field is not safe. PyTorch optimizers expose common values through param groups, but third-party optimizers may cache values elsewhere or require structured updates.

The package should define an explicit binding contract:

```python
class OptimizerBinding(Protocol):
    name: str
    def read(self, optimizer: Optimizer) -> Value: ...
    def apply(self, optimizer: Optimizer, value: Value) -> None: ...
```

Built-ins should cover:

- a param-group scalar applied to all selected groups;
- a separate gene per selected param group;
- multiplicative scaling that preserves existing group ratios;
- one element of a tuple field such as `betas[0]`;
- a custom getter/setter escape hatch.

Missing fields should fail immediately. The package should not silently invent defaults or skip an unsupported optimizer.

The scheduler sees a logical genome. The binding layer alone knows how that genome maps to the runtime optimizer.

Changing momentum or beta values while retaining inherited moments is an intentional abrupt schedule transition. The package should not rewrite optimizer history unless a specific binding explicitly defines such a transformation.

### 6.6 Fitness reporter and replicated evaluation data

Lightning's default distributed validation sampler gives each rank a different validation subset. That is useful for evaluating one synchronized model and inappropriate for ranking different models.

The initial integration should provide a `ReplicatedFitnessSampler` or helper that makes every rank evaluate the same deterministic fitness set while leaving the training dataloader normally sharded.

The fitness value must remain rank-local until the CBT callback gathers it. A user metric logged with `sync_dist=True` has already destroyed the information needed for member ranking.

Preferred surface:

- a small `FitnessReporter`/mixin method that accumulates a scalar on each rank;
- an explicit metric name fallback for existing models, documented to require `sync_dist=False`;
- an optional step-output extractor for models that do not use Lightning logging.

The callback then gathers one final scalar per member with the public strategy gather API.

The fitness data should be deterministic enough that member differences reflect optimizer behavior rather than rank-specific validation samples or augmentations.

### 6.7 Clan checkpoint format

Ordinary Lightning DDP checkpointing saves only global rank 0 because replicas are assumed equivalent. That is not authoritative for a divergent clan.

The clan checkpoint should be a directory-like artifact containing:

```text
manifest.json
member-00000.ckpt
member-00001.ckpt
...
```

The manifest should include at least:

- format version;
- package, Lightning, PyTorch, and optional Ray versions;
- world size;
- committed generation and global step;
- member-slot to shard mapping;
- scheduler state authority;
- checkpoint completion marker;
- hashes or sizes sufficient to detect missing shards.

Each member shard can initially be a complete Lightning checkpoint. This duplicates some common state but is the simplest auditable correct format. Deduplication at common-state boundaries is a later optimization.

The strategy must override Lightning's global-rank-zero save gate, coordinate one shard per rank, barrier, then have rank 0 commit the manifest. A checkpoint without a committed manifest is incomplete and must not be resumed. Lightning's `CheckpointIO` interface can remain the low-level storage backend, but it cannot own the clan transaction: it receives only one already-assembled local checkpoint and is currently an experimental API. Distributed coordination, shard naming, manifest authority, and rank-specific restore therefore remain strategy-owned, with storage delegated where useful.

Standard `ModelCheckpoint` should not be the authoritative resume mechanism initially. Its per-rank metric decisions can diverge when monitoring member-local fitness. Provide a dedicated `ClanCheckpointCallback` that saves committed clan state. Standard ModelCheckpoint may still be used for champion exports or genuinely clan-global metrics.

## 7. Generation transition and failure ordering

The generation boundary should be treated as a transaction:

1. finish an optimizer step;
2. complete comparable validation;
3. gather member fitness;
4. rank 0 creates a plan;
5. broadcast the plan;
6. transfer source model and optimizer state;
7. apply target genomes;
8. clear gradients;
9. verify local applied-config hashes and source-state checksums where appropriate;
10. barrier;
11. commit scheduler state and generation number;
12. log the transition;
13. optionally save a committed clan checkpoint;
14. resume training.

No durable checkpoint should describe a partially applied transition.

If any rank fails before commit, the distributed job should fail. Recovery starts from the previous committed clan checkpoint. The runtime should not attempt to guess which members completed the transition.

Debug verification may compare model/config hashes across ranks immediately after reseeding. Such checks should be boundary-only and removable from performance runs; they do not belong in the training hot path.

## 8. Precision, optimizer, and framework support boundaries

These are initial engineering support limits, not permanent scientific limits.

### Supported first

- Lightning 2.6.x;
- PyTorch DDP with fixed world size;
- single-node multi-GPU and CPU test execution;
- automatic optimization;
- one optimizer;
- SGD and AdamW as first verified optimizers;
- 32-bit precision;
- BF16 mixed precision after a GPU contract test;
- fixed integer gradient accumulation;
- deterministic replicated fitness evaluation;
- rank-sharded clan checkpoints;
- local launcher and optional Ray Train launcher.

The current scaffold's broad dependency range is provisional. Before the Lightning integration is released, package metadata should be tightened to the versions actually covered by the compatibility matrix rather than implying support for untested Lightning or PyTorch releases.

### Explicit integration gates

**FP16 mixed precision:** Lightning scales each local loss before backward. All ranks must use the same GradScaler scale before DDP reduces gradients. Otherwise the shared gradient combines different numerical scales. FP16 support requires a probe and likely a globally synchronized scaler policy.

**Lightning LR schedulers:** if a Lightning scheduler writes a CBT-controlled optimizer field, there are two sources of truth. Initially reject this configuration. Later support can require explicit field ownership.

**Gradient accumulation schedulers:** dynamic accumulation can place validation inside a partially accumulated step. Initially require fixed accumulation and configure fitness validation to align with completed optimizer steps.

**SyncBatchNorm:** synchronizes forward statistics and changes the member-independence contract. Reject initially.

**FSDP, DeepSpeed, ZeRO, distributed optimizers:** these shard one model's state across ranks, while CBT defines each rank as a separate full member. They are incompatible with the initial rank-as-member design.

**post-local-SGD/model averaging:** directly counteracts intentional divergence. Reject.

**custom DDP communication hooks:** may change the shared-gradient semantics. Do not claim support until tested.

**compiled optimizers, CUDA graphs, and elastic world-size changes:** defer until state mutation and checkpoint contracts are proven.

**manual optimization and multiple optimizers:** possible later, but they complicate the definition of a completed member step and genome application. Do not include in the first supported API.

## 9. Ray integration

Ray should remain optional and should not be a core dependency.

Ray's current `RayDDPStrategy` is a small `DDPStrategy` subclass that supplies Ray's root device and distributed sampler rank/world-size values. `prepare_trainer()` accepts subclasses of `RayDDPStrategy`.

The clean adapter is therefore:

```python
class RayClanDDPStrategy(ClanDDPBehaviorMixin, RayDDPStrategy):
    ...
```

The shared clan behavior should live in one mixin or focused helper used by both:

- `ClanDDPStrategy(ClanDDPBehaviorMixin, DDPStrategy)`
- `RayClanDDPStrategy(ClanDDPBehaviorMixin, RayDDPStrategy)`

Ray Train can merge rank-specific checkpoint files reported by multiple workers into one persisted checkpoint directory. A `RayClanReportCallback` should:

- report at committed generation boundaries rather than only epoch ends;
- have every worker report its uniquely named member shard;
- attach only clan-global summary metrics from rank 0;
- rely on Ray CheckpointConfig for remote retention;
- restore the merged directory through the clan strategy.

Ray Tune PBT remains the full-PBT baseline and an optional outer scheduler for independent trials. It should not be composed with the inner scheduler as though both controlled the same member population.

HyperBand/ASHA can later schedule multiple independent clan trials outside CBT. Ray Tune supports one trial scheduler at a given Tune level; nested inner CBT plus outer ASHA is conceptually valid because they operate on different populations.

## 10. Raw DDP reference implementation

A raw PyTorch implementation is still valuable, but its responsibility must remain narrow:

- demonstrate the exact shared-gradient/divergent-optimizer step;
- implement the same scheduler plan contract;
- implement the same tensor state transfer format;
- provide a debugging oracle when Lightning behavior is questioned;
- support the scientific harness if a framework issue must be isolated.

It should not grow logging, configuration, checkpoint retention, trainer callbacks, or experiment management that Lightning and Ray already own.

The raw reference and Lightning plugin should share the pure scheduler, mutation, optimizer-binding, and tensor-transfer code. Only the lifecycle adapter differs.
