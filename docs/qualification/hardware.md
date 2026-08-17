# Hardware and failure qualification

Status: executable local harnesses; support expands only from recorded passing evidence.

The hardware contracts use a tiny two-layer regression model, AdamW, fixed synthetic data,
and two training batches per invocation. They exercise the real Ray Tune + Lightning +
PyTorch Clan path without downloading a model or dataset.

## Local CUDA/NCCL

Requirements:

- a development checkout installed with `python -m pip install -e '.[dev]'`;
- at least two visible CUDA GPUs; and
- enough CPU capacity to run two Tune members.

Run:

```bash
python -m pytest tests/hardware/test_cuda_function_path.py -vv
```

The contract requests one GPU per Tune trial/member. It requires both members to report CUDA
devices, an NCCL backend, DDP world size two, successful real training, restored nonzero
Lightning progress on the next generation, and application of each receiving child genome.
If fewer than two CUDA devices are visible, the test skips.

A passing run should be recorded with GPU model, driver/CUDA environment, Python, Ray,
Lightning, PyTorch, OS, and commit SHA before STATUS is broadened to claim CUDA/NCCL support.

## Physical multi-node

This test attaches to an already-running Ray cluster. Because the workload checkpoints, Ray
Tune requires storage shared by every node, such as NFS or supported cloud storage. The
repository must also be importable by workers; install the same checkout/environment on the
participating nodes.

Constrain the cluster so the two one-CPU test members actually land on distinct machines—for
example, expose one schedulable test CPU on each intended node. Then set:

```bash
export CLAN_RUN_MULTI_NODE=1
export CLAN_TEST_STORAGE_PATH=/path/mounted/on/every/node
# Optional when `ray.init(address="auto")` is not sufficient:
export CLAN_TEST_RAY_ADDRESS=host:port
python -m pytest tests/hardware/test_multi_node_function_path.py -vv
```

The contract first requires at least two live Ray nodes, then runs the real tiny Clan for two
generations and fails unless the two reported node fingerprints differ. A run in which both
members land on one node does not count as multi-node evidence.

Record cluster topology, storage type, framework versions, OS, and commit SHA with any pass.

## Active-collective peer exit

This test intentionally terminates one member process after DDP setup. Do not enable it as an
ordinary smoke test.

```bash
export CLAN_RUN_DESTRUCTIVE_FAILURE=1
python -m pytest \
  tests/framework_contracts/test_failure_boundaries.py::test_active_collective_peer_exit_is_bounded \
  -vv
```

The current contract requires the Tune experiment to terminate with recorded errors within a
bounded interval. It does not claim transparent in-place collective recovery or continuation
after losing a live DDP participant. Those would require a stronger design and separate
evidence.

## Evidence rule

Self-skipping hardware tests make one checkout usable on CPU-only and GPU machines; a skip is
not a pass. Do not broaden public support from the presence of these files. Record a concrete
passing environment first, then update STATUS/qualification docs in the same change.
