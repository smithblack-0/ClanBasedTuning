# Lightning integration assessment for ClanBasedTuning

Status: superseded historical assessment; see `native_trial_build_contract.md`

Date: 2026-07-21

## Executive conclusion

ClanBasedTuning should be implemented as a **Lightning-first plugin with a pure clan scheduler**, using PyTorch DDP as the shared-gradient data plane.

The recommended primary design is:

1. **`ClanScheduler`** — the population policy and the heart of the product.
2. **`ClanTuningCallback`** — the Lightning lifecycle adapter that invokes the scheduler at synchronous generation boundaries.
3. **`ClanDDPStrategy`** — a focused `DDPStrategy` subclass that configures intentionally divergent replicas, performs live state transfer, and preserves rank-local state in checkpoints.
4. **optimizer bindings** — explicit adapters between logical scheduler genes and already-constructed optimizer fields.
5. **fitness support** — a replicated evaluation sampler plus an explicit member-local fitness reporter.
6. **a raw DDP reference loop** — an executable oracle for the algorithm and state-transfer semantics, not a competing framework.
7. **an optional Ray adapter** — a thin subclass of Ray's Lightning DDP strategy and a Ray reporting callback. Ray remains an outer launcher, persistence layer, and experiment orchestrator; it does not own the inner clan scheduler.

A custom Lightning fit loop is not justified. Stock `DDPStrategy` configuration alone is also not sufficient because exact checkpoint restore, non-rank-zero state persistence, and efficient winner transfer require strategy-level behavior.

The main engineering difficulty is **not gradient reduction**. Ordinary DDP already performs the desired reduction while permitting local optimizer steps to produce divergent parameter values. The difficult work is making validation, state transfer, precision, checkpointing, logging, and recovery correct under a condition that ordinary DDP frameworks normally assume cannot occur.

## 1. Contract being implemented

One Lightning distributed job is one clan. One DDP rank is one clan member.

Every member has:

- the same model and optimizer structure;
- separate parameter values and registered buffers after divergence begins;
- separate optimizer state;
- separate optimizer hyperparameter values;
- a separate training minibatch stream;
- a stable logical member slot for the duration of a fixed-world-size run.

Every training step:

1. runs a local forward and backward pass;
2. contributes the local gradient to ordinary DDP all-reduction;
3. receives the same reduced gradient as the other members;
4. applies that gradient through its own optimizer state and hyperparameters;
5. produces a distinct next parameter state.

At a synchronous generation boundary:

1. every member is evaluated on comparable fitness data;
2. member-local fitness values are gathered;
3. the scheduler chooses the source member and the next optimizer configurations;
4. the source model, buffers, and optimizer state are transferred to the clan;
5. rank-local optimizer hyperparameters are applied;
6. the new generation is committed only after all ranks confirm the transition;
7. the transition and lineage are logged and may be checkpointed.

The scheduler decides **what should happen**. The Lightning adapter performs **when it happens**. The strategy performs **how distributed state moves and persists**.

## 2. Source review scope

The assessment followed the actual call paths rather than relying on framework names or documentation summaries.

Reviewed locally against Lightning 2.6.5 and PyTorch 2.10.0:

- `lightning/pytorch/strategies/ddp.py`
- `lightning/pytorch/strategies/strategy.py`
- `lightning/pytorch/trainer/trainer.py`
- `lightning/pytorch/trainer/connectors/checkpoint_connector.py`
- `lightning/pytorch/trainer/connectors/callback_connector.py`
- `lightning/pytorch/trainer/connectors/data_connector.py`
- `lightning/pytorch/loops/evaluation_loop.py`
- `lightning/pytorch/loops/training_epoch_loop.py`
- `lightning/pytorch/loops/optimization/automatic.py`
- `lightning/pytorch/plugins/precision/amp.py`
- `torch/nn/parallel/distributed.py`

Reviewed from Ray master:

- `python/ray/tune/schedulers/pbt.py`, blob `4dac19081f8c725afcec3286f9fd0c4e9478c471`
- `python/ray/train/lightning/_lightning_utils.py`, blob `72706c0e6a69cbf7f2d236d24511730b565c8de4`

The companion source ledger records concrete findings and probe outputs.

## 3. What Lightning and DDP already provide

### 3.1 Ordinary DDP is the correct gradient data plane

Lightning's `DDPStrategy.setup()` moves the model to its device, wraps it in PyTorch `DistributedDataParallel`, and constructs optimizers after wrapping. Arbitrary DDP constructor options are forwarded through the strategy.

PyTorch DDP verifies model structure and synchronizes initial parameter values when `init_sync=True`. During training it reduces gradients. It does not continually broadcast parameter values after local optimizer steps.

Therefore the central training behavior does not require a custom reducer:

- keep DDP initialization and shape checking;
- keep ordinary gradient all-reduction;
- apply rank-local optimizer hyperparameters after reduction;
- intentionally allow parameter values to diverge.

A source probe confirmed the exact contract on two Lightning CPU ranks:

- the post-DDP gradient was `5.0` on both ranks;
- rank 0 applied learning rate `0.05` and reached weight `0.75`;
- rank 1 applied learning rate `0.20` and reached weight approximately `0.0`.

The models diverged while consuming the same reduced gradient.

### 3.2 Runtime buffer broadcasting must be disabled

PyTorch DDP defaults to `broadcast_buffers=True`. Before forward passes, registered buffers can be overwritten from an authoritative rank. This is correct for ordinary identical replicas and incorrect for clan members with distinct model trajectories.

`ClanDDPStrategy` must enforce:

```python
broadcast_buffers=False
```

This does not mean buffers are ignored. Buffers are rank-local during training and must be transferred with the selected source member at a generation boundary.

A probe confirmed that a rank-local buffer stayed divergent during training and was then copied correctly when rank 1 reseeded rank 0.

`SyncBatchNorm` is a separate coupling mechanism that synchronizes forward statistics. It should be unsupported initially rather than silently changing the scientific contract.

### 3.3 Public Strategy and Callback hooks are sufficient

The required lifecycle can be built with public extension surfaces:

- custom `DDPStrategy` subclass;
- normal callback hooks;
- strategy `all_gather`, `broadcast`, and barriers for small control values;
- direct tensor collectives owned inside the strategy for large state transfer;
- callback `state_dict` and `load_state_dict` for scheduler state;
- custom strategy checkpoint save/load behavior.

Replacing Lightning's fit loop would gain control at the price of depending on internal loop implementation. The current source does not justify that cost.

## 4. What Ray PBT contributes conceptually

Ray PBT is closely related at the **scheduler/executor boundary**, not at the resource-pool boundary.

Ray separates:

- per-member records and scheduler policy;
- result reporting;
- synchronous or asynchronous perturbation timing;
- exploit/explore decisions;
- checkpoint transfer;
- trial pause/resume and resource scheduling.

The useful pattern is that `PopulationBasedTraining` decides which trial should clone which source and how the configuration should mutate, while `TuneController` owns the runtime actions.

ClanBasedTuning should preserve this separation:

- `ClanScheduler` replaces the decision portion;
- `ClanTuningCallback` and `ClanDDPStrategy` together replace the execution controller;
- DDP ranks replace Tune trials as members;
- the process group is fixed and synchronous, so trial pausing and resource allocation disappear.

Ray PBT behavior that should **not** be reused as an inner mechanism:

- `Trial` and `TuneController` dependencies;
- asynchronous perturbation;
- time-multiplexing members through a resource pool;
- disk checkpoint round-trips for ordinary exploit operations;
- a core dependency on Ray search-space classes;
- quantile selection as a mandatory policy.

Ray remains useful outside the clan for launching workers, persistent distributed checkpoints, outer comparisons, and running full-PBT baselines.

## 5. Options considered

### Option A — configured stock `DDPStrategy` plus one callback

The callback would configure optimizer values, gather fitness, run selection, broadcast models, transfer optimizer state, save all rank states, restore them, and manage lineage.

**Why it is attractive:** minimal class count.

**Why it fails the design review:**

- Lightning's default strategy saves only rank 0 state;
- default checkpoint restore ordering can destroy divergent restored state;
- large tensor transfer does not belong in a lifecycle callback;
- checkpoint, distributed mechanics, scheduler policy, and validation would collapse into one owner;
- the callback would become a second training framework hidden inside Lightning.

**Decision:** reject.

### Option B — `ClanDDPStrategy` + `ClanTuningCallback` + pure scheduler

**Strategy owns:**

- DDP configuration constraints;
- world/rank information;
- model/buffer/optimizer transfer;
- barriers and tensor collectives;
- clan checkpoint save/load mechanics;
- delayed restore ordering.

**Callback owns:**

- generation boundary detection;
- local fitness extraction;
- gathering member reports;
- invoking the scheduler on rank 0;
- broadcasting the small transition plan;
- ordering transfer, mutation, commit, logging, and checkpoint requests.

**Scheduler owns:**

- selection;
- mutation;
- lineage;
- policy RNG;
- scheduler state and schedule reconstruction.

**Decision:** adopt.

### Option C — custom Lightning fit or training loop

**Advantage:** exact control over optimizer-step boundaries and validation.

**Problems:**

- uses internal loop contracts;
- duplicates Lightning behavior around accumulation, precision, schedulers, logging, exceptions, and restart progress;
- makes every Lightning release an integration rewrite;
- current public hooks already support the required lifecycle.

**Decision:** reject unless a later contract test proves a specific public-hook limitation.

### Option D — Fabric or raw PyTorch as the primary product

**Advantage:** clear ownership and minimal hidden behavior.

**Problem:** users must adopt a new training loop, undermining the engineering-usability contribution.

**Decision:** keep a small raw DDP reference implementation as the behavioral oracle and debugging baseline. Do not make it the primary user surface.

### Option E — make Ray PBT the inner scheduler

**Advantage:** mature PBT implementation.

**Problem:** its member is a Tune trial. A clan member is a rank inside one trial and one process group. Adapting Tune's scheduler would require fake trials or would restore the incompatible member/resource-pool split.

**Decision:** implement an independent scheduler with similar policy/executor separation. Offer Ray only as optional outer orchestration.

## Detailed design artifacts

The implementation detail is separated so that the decision report remains reviewable:

- [Component and lifecycle contracts](lightning_component_contracts.md)
- [Build sequence and verification plan](lightning_build_plan.md)
- [Source review and contract-probe ledger](source_review_ledger.md)

## Final recommendation

Proceed with the package using **Option B**:

- a pure, framework-independent `ClanScheduler` as the main contribution;
- a focused Lightning callback as lifecycle glue;
- a custom DDP strategy only for the distributed behaviors Lightning cannot represent under its ordinary identical-replica assumptions;
- a raw DDP reference as an oracle;
- Ray as an optional launcher and distributed checkpoint/reporting adapter.

This design makes the engineering usability the center of the contribution without building another training framework. It uses Lightning for the responsibilities Lightning already handles, but does not pretend that ordinary DDP checkpointing, validation, or precision assumptions remain correct after replicas intentionally diverge.
