# ClanBasedTuning project status

Last updated: 2026-08-14

## Current implementation

The active branch contains a complete initial Clan Tuning function path built on Ray Tune,
Lightning, and PyTorch. The ordinary user surface is now the same shape as those frameworks:

- the user's Ray function receives the current config/genome directly;
- `ClanScheduler` is supplied through `TuneConfig(scheduler=...)`;
- the fitness `metric` and `mode` are supplied once through `TuneConfig`;
- `ClanDDPStrategy` is supplied through Lightning's `Trainer(strategy=...)`;
- `ClanTuneReportCallback` is supplied through Lightning's callback interface; and
- Ray's per-trial resource annotation determines the one device/process assigned to each
  Clan member. Ordinary users do not need to repeat `devices=1` in the Trainer.

The prior `ClanScheduler.wrap(train)` user step has been removed. The scheduler registers
trial identity/topology in an internal Ray registry before launch, and the Lightning
strategy discovers that assignment from the current Tune trial.

Mutation configuration is a plain nested dictionary. The former user-facing `MutationSpec`
object is now an internal validated representation rather than an API requirement.

Production CBT contains no genome-application function, optimizer schema, inferred
optimizer mapping, restore callback, or post-load application hook. Examples and contracts
show the user's optimizer edits inline at the point where they matter.

## Executable qualification

The complete single-node CPU contract uses real Ray + Lightning + PyTorch rather than mocks.
It covers two concurrent members across repeated generation transitions and establishes:

- one framework-managed DDP world and one common reduced gradient;
- partitioned training data;
- replicated Lightning-managed validation data;
- member-local divergence from user-applied optimizer policy;
- common deterministic winner selection;
- winner-only persistent Clan continuation checkpointing while retaining Lightning's
  checkpoint barrier;
- Ray transfer of the selected continuation;
- inherited model state, optimizer momentum/history, and Lightning loop progress;
- direct use of the newly assigned Tune config in userspace;
- independent sibling mutation of the selected parent for every next member; and
- persistent CBT checkpoint count scaling with rounds rather than population size times
  rounds.

The framework suite also intentionally fails the post-checkpoint resumed invocation, shuts
down Ray, starts a new Ray runtime, restores the Tune experiment through `Tuner.restore`,
and requires the Clan to reconstruct its runtime and continue. This distinguishes
experiment recovery from the easier within-run PBT checkpoint transition.

The currently qualified complete environment remains Python 3.11, Ray 2.56.1, Lightning
2.6.5, PyTorch 2.10.0, Linux CI, one node, and CPU execution. Dependency-light package tests
also run on Python 3.13.

## Repository readiness

The repository is being judged separately from the mechanics implementation. Current
signals are:

| Area | Current state |
| --- | --- |
| Source/package layout | Good: standard `src/` layout and `pyproject.toml`. |
| Ordinary API shape | Improved: native Ray scheduler + Lightning strategy/callback; no custom trainable wrapper. |
| Configuration | Improved: plain mutation dictionaries; metric/mode configured once in Tune; device topology configured through Ray. |
| User documentation | Good foundation: README quickstart, detailed API guide, support boundary, restore guidance. Needs later real-workload guidance. |
| Examples | One complete runnable CPU mechanics example. Realistic GPU/scientific examples await GPU qualification. |
| Unit tests | Core selection/controller and mutation validation are covered. More focused scheduler/runtime error-path tests remain useful. |
| End-to-end tests | Strong for the qualified CPU path, including full restore and interrupted-experiment restore. |
| Failure testing | Pre-DDP timeout exists; active-collective member failure/recovery remains unqualified. |
| CI | Linux, Python 3.11/3.13, lint/format, unit/framework contracts. Wheel/sdist installation is not yet exercised by CI. |
| Static typing | Type annotations exist, but there is no type-checker gate or PEP 561 support claim yet. |
| Coverage reporting | No coverage metric/gate; test adequacy is currently reviewed contract-by-contract. |
| Packaging/release | Repository install works through the optional `ray` extra. No published-package/release process is claimed. |
| License | **Missing.** Production/open-source adoption is blocked until the project owner chooses and adds a license. |
| Security policy | Missing; should be added before a production-support claim if external users are expected. |
| Version/release history | Pre-release version exists; changelog/release policy is not yet established. |
| Observability | Ray/Lightning logs and reported metrics are available; Clan-specific transition diagnostics remain limited. |
| GPU/multi-node | Not qualified yet. |
| Scientific evidence | Mechanics only; realistic optimizer-policy/overhead studies remain future evidence. |

The absence of a license is a legal/adoption blocker, not an implementation detail; it
cannot be selected automatically by engineering work. CI workflow expansion also remains a
separate approved change rather than being silently edited during this pass.

## Scientific validity boundary

CBT deliberately does not interpret Tune config keys, but valid Clan variation must be
applied after the common gradient is computed. Optimizer-side policy such as learning rate,
weight decay, momentum, or betas is the intended target. Varying model architecture,
training data, forward behavior, or loss would make members contribute gradients for
different training problems and is not valid Clan Tuning.

Candidate fitness must remain member-local until CBT's population exchange. Users who
replace Lightning's automatically managed validation sampler are responsible for keeping
candidate evaluation comparable.

## Known implementation/support limits

The current complete path does not yet establish:

- CUDA/NCCL;
- multi-node execution;
- actor reuse;
- predictable recovery after a member disappears inside an active distributed collective;
- arbitrary/custom/sharded checkpoint plugins;
- explicitly user-supplied distributed validation-sampler semantics;
- ClanFSDP/model-sharded execution; or
- realistic scientific performance and overhead.

The complete Clan must fit concurrently. The current runtime has a bounded rendezvous wait
but no separate CBT watchdog around a framework-owned active collective.

## Current work

The CPU mechanics path is no longer treated as equivalent to repository readiness. The
current pass is productization: remove development scaffolding, normalize the public API to
Ray/Lightning conventions, qualify interrupted-run restoration, improve documentation and
examples, and record readiness gaps explicitly before expanding hardware support.

The next capability milestone remains complete-cohort/failure hardening followed by GPU
qualification. See [`docs/plan.md`](docs/plan.md) and
[`docs/qualification/function_api.md`](docs/qualification/function_api.md).
