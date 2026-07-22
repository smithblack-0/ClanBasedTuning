# Framework source review and contract-probe ledger

Date: 2026-07-21

This ledger records the evidence used by the Lightning integration assessment.
It is not an implementation plan by itself.

## Source baselines

### Lightning

Locally inspected package version: `2.6.5`

Primary files:

- [`DDPStrategy`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/strategies/ddp.py)
- [`Strategy`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/strategies/strategy.py)
- [`Trainer`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/trainer/trainer.py)
- [`_CheckpointConnector`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/trainer/connectors/checkpoint_connector.py)
- [`_CallbackConnector`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/trainer/connectors/callback_connector.py)
- [`_DataConnector`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/trainer/connectors/data_connector.py)
- [`_EvaluationLoop`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/loops/evaluation_loop.py)
- [`_TrainingEpochLoop`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/loops/training_epoch_loop.py)
- [`_AutomaticOptimization`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/loops/optimization/automatic.py)
- [`MixedPrecision`](https://github.com/Lightning-AI/pytorch-lightning/blob/2.6.5/src/lightning/pytorch/plugins/precision/amp.py)

Official extension documentation:

- [Custom strategies](https://lightning.ai/docs/pytorch/stable/extensions/strategy.html)
- [Plugins and CheckpointIO](https://lightning.ai/docs/pytorch/stable/extensions/plugins.html)
- [Distributed checkpoints](https://lightning.ai/docs/pytorch/stable/common/checkpointing_expert.html)

### PyTorch

Locally inspected package version: `2.10.0+cpu`

Primary file:

- `torch/nn/parallel/distributed.py`

Relevant verified behavior:

- `init_sync=True` verifies parameter shapes and synchronizes initial parameters and buffers from rank 0;
- `broadcast_buffers=True` enables runtime buffer synchronization;
- DDP's reducer synchronizes gradients, not post-optimizer parameter values.

### Ray

PBT source reviewed from current master:

- [`python/ray/tune/schedulers/pbt.py`](https://github.com/ray-project/ray/blob/master/python/ray/tune/schedulers/pbt.py)
- blob: `4dac19081f8c725afcec3286f9fd0c4e9478c471`

Lightning adapter reviewed from current master:

- [`python/ray/train/lightning/_lightning_utils.py`](https://github.com/ray-project/ray/blob/master/python/ray/train/lightning/_lightning_utils.py)
- blob: `72706c0e6a69cbf7f2d236d24511730b565c8de4`

Official documentation:

- [Ray Train with Lightning](https://docs.ray.io/en/latest/train/getting-started-pytorch-lightning.html)
- [Ray distributed checkpointing](https://docs.ray.io/en/latest/train/user-guides/checkpoints.html)

## Source findings

| Area | Evidence | Design consequence |
|---|---|---|
| DDP setup | Lightning wraps the device-local model, then initializes optimizers | Rank-local optimizer configuration can be applied after setup without replacing Trainer |
| DDP kwargs | `DDPStrategy` forwards arbitrary constructor kwargs | `broadcast_buffers=False` can be enforced in a subclass |
| Initial sync | PyTorch DDP syncs parameters/buffers at construction | Keep `init_sync=True` for fresh start and structural verification |
| Runtime parameter sync | DDP does not broadcast parameters after optimizer steps | Different optimizer hyperparameters can intentionally diverge replicas |
| Buffer sync | DDP broadcasts buffers before forward by default | Disable it and transfer buffers only at generation boundaries |
| Default restore order | Lightning restores model/callback state before strategy setup | Exact divergent resume requires `restore_checkpoint_after_setup=True` |
| Optimizer restore | Optimizers restore after strategy setup and model restore | `on_train_start` is the safe activation/reconciliation hook |
| Default checkpoint save | Base Strategy writes only on rank 0 | Clan checkpointing must persist every member shard |
| Callback order | ModelCheckpoint callbacks are moved to the end | CBT transition can complete before a dedicated checkpoint callback saves |
| Validation | Lightning injects distributed samplers | Fitness evaluation needs an explicitly replicated validation sampler |
| Metric sync | `sync_dist=True` reduces metrics | Member fitness must remain local until CBT gathers it |
| Plateau schedulers | Lightning steps them after validation | Reject two-owner configurations for CBT-controlled fields |
| FP16 AMP | each rank scales loss before backward | GradScaler scale must be common across ranks before shared reduction |
| Ray PBT | scheduler decides; TuneController executes | Preserve policy/executor split, replace trial controller with clan adapter |
| Ray DDP | RayDDPStrategy only supplies device and sampler context | A Ray-specific clan strategy can be a thin subclass |
| Ray checkpoints | worker checkpoints can merge into one directory | Natural transport for rank-specific clan shards |

## Contract probes

The probes used Lightning 2.6.5, PyTorch 2.10.0, two CPU ranks, Gloo, and `DDPStrategy(start_method="fork")`.
They tested framework contracts only, not the scientific effectiveness of clan tuning.

### Probe 1 — shared gradients with divergent optimizer application

Setup:

- identical one-weight models;
- distinct rank-local minibatches;
- ordinary DDP reduction;
- rank 0 learning rate `0.05`;
- rank 1 learning rate `0.20`;
- `broadcast_buffers=False`.

Result after two optimizer steps:

```text
rank 0: weight = 0.5625, lr = 0.05
rank 1: weight = -0.74999994, lr = 0.20
```

Conclusion: Lightning DDP allows intentional parameter divergence after local optimizer steps.

### Probe 2 — common reduced gradient, local fitness, and nonzero-rank reseed

Setup:

- one optimizer step;
- callback captured the gradient immediately before optimizer step;
- both ranks evaluated the same replicated validation examples;
- fitness was logged without distributed synchronization;
- rank 1 was used as the simulated winner;
- model parameter and registered buffer were broadcast from rank 1.

Result:

```text
rank 0 gradient after DDP: 5.0
rank 1 gradient after DDP: 5.0

rank 0 weight before reseed: 0.75
rank 1 weight before reseed: approximately 0.0

rank 0 local fitness: 1.40625
rank 1 local fitness: approximately 0.0

both ranks after reseed:
weight: approximately 0.0
buffer: 2.0
```

Conclusion:

- the reduced gradient was identical;
- optimizer settings produced distinct models and fitness;
- unsynchronized local validation remained distinct;
- an arbitrary nonzero source rank could reseed parameters and buffers.

### Probe 3 — exact divergent Lightning resume

A minimal strategy override implemented:

- `restore_checkpoint_after_setup=True`;
- one checkpoint shard per rank;
- rank-specific shard loading.

Saved state:

```text
rank 0: weight 0.75, lr 0.05
rank 1: weight approximately 0.0, lr 0.20
```

State observed in `on_train_start` after resume:

```text
rank 0: weight 0.75, lr 0.05, global_step 1
rank 1: weight approximately 0.0, lr 0.20, global_step 1
```

Conclusion: a small strategy-level persistence override is sufficient to preserve divergent model and optimizer state through Lightning's normal restore lifecycle.

## Unverified gates

The following require GPU or larger integration tests:

- NCCL tensor-tree transfer performance;
- AdamW optimizer-state transfer at realistic model size;
- BF16 behavior;
- synchronized FP16 GradScaler behavior;
- multi-node checkpoint storage and restore;
- Ray merged checkpoint resume;
- interaction with gradient accumulation at mid-epoch validation boundaries;
- failure injection during a generation transition;
- Lightning version compatibility outside 2.6.x.
