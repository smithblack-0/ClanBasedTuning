# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: distributed training
that shares gradients across a population while adapting a Tune genome online through
population selection.

## Function API

The active integration follows Ray Tune's ordinary function-trainable/PBT shape:

```python
def train(genome): ...
```

Ray supplies each member's current genome. ClanBasedTuning selects the common parent and
mutates the next genomes, but it does not interpret or apply those values. On resume, user
code restores the selected parent's state and explicitly applies the current genome before
training continues.

A minimal Lightning path uses:

```python
from clan_based_tuning import ClanDDPStrategy, ClanScheduler, ClanTuneReportCallback
```

`ClanScheduler.wrap(train)` carries the hidden Clan member/rendezvous context without
adding private fields to the user's genome. `ClanDDPStrategy` lets the independently
launched Tune trials form the shared Lightning/PyTorch DDP world. The reporting callback
compares member-local fitness and reports exactly one persistent continuation checkpoint
per Clan round.

The complete runnable mechanics example is
[`examples/simple_clan_tuning.py`](examples/simple_clan_tuning.py). The explicit userspace
genome-application code is intentionally shown there rather than hidden behind a CBT
optimizer helper.

## Current package surface

The dependency-free core exports:

- `ClanController`, the small worker-side fitness/selection primitive; and
- `MutationSpec`, a bounded linear or logarithmic scalar mutation rule.

With the Ray integration extra installed, the package root lazily exposes:

- `ClanScheduler`;
- `ClanDDPStrategy`; and
- `ClanTuneReportCallback`.

```bash
python -m pip install -e '.[ray]'
```

Importing the framework-independent package does not require Ray or Lightning.

## Distributed ownership

The initial path uses one Tune trial as one stable Clan member and one externally launched
Lightning process/rank.

Ray Tune owns trial execution, resources, PBT pause/resume behavior, checkpoint transfer,
and configuration transfer. Lightning/PyTorch own DDP initialization, backend/device
selection, shared-gradient communication, checkpoint construction, and distributed
barriers. CBT supplies only the cross-trial Clan topology, population policy, scalar
fitness exchange over the established group, and winner-only CBT checkpoint write gate.

Production CBT does not select GLOO, NCCL, CPU, or CUDA and does not initialize or destroy
a process group. Users may still pass Lightning's ordinary DDP backend options when they
need an explicit backend.

## Checkpoint storage

A CBT round persistently writes only the selected member's continuation. All DDP ranks
participate in Lightning's checkpoint construction and barrier, but losing ranks do not
delegate a CBT round checkpoint to `CheckpointIO` and do not report a Ray checkpoint.

The repeated native contract instruments `CheckpointIO` directly and verifies one
physical Lightning checkpoint write per Clan round rather than one per population member.
User-configured additional Lightning checkpoints remain separate from this CBT storage
contract.

## Current evidence and limits

A real Ray 2.56.1 / Lightning 2.6.5 / PyTorch 2.10 CPU contract runs two concurrent Tune
function trials through repeated Clan boundaries. It directly exercises shared DDP
training, member-local fitness comparison, sole checkpoint persistence, native PBT
checkpoint/configuration reassignment, and explicit userspace genome application after
optimizer-state restore.

The production code is backend-neutral, but CUDA/NCCL, multi-node execution, flexible gang
admission, actor reuse, broader failure recovery, arbitrary optimizer layouts, and later
ClanFSDP execution require separate qualification before support is claimed.

## Documentation

Start with [`docs/README.md`](docs/README.md). The governing product roadmap is
[`docs/product_roadmap.md`](docs/product_roadmap.md), public usage is in
[`docs/api.md`](docs/api.md), current integration ownership is in
[`docs/design/integration.md`](docs/design/integration.md), and live project status is in
[`STATUS.md`](STATUS.md).

## Development

Python 3.11 through 3.13 is supported for the framework-independent package. The current
Ray-native contract runs on Python 3.11.

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
