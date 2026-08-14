# ClanBasedTuning project status

Last updated: 2026-08-14

## Current corrective branch

The function-API branch now contains the corrected architecture intended for continued
maintenance. The public user shape remains:

- an ordinary Ray Tune function receiving the current genome/config;
- `ClanScheduler` through `TuneConfig(scheduler=...)`;
- `ClanDDPStrategy` through Lightning's strategy interface;
- `ClanTuneReportCallback` through Lightning callbacks; and
- one Ray trial/resource allocation per Clan member.

Genome application remains entirely userspace.

## Architecture correction

The corrective implementation removes inheritance from Ray's stock PBT internals. The
scheduler owns the small synchronous Clan transition and isolates the unavoidable Tune
checkpoint/config transfer details in `ray_compat.py`. Package users are therefore not tied
to one Ray minor release merely to preserve PBT subclass internals.

The same wave:

- removes the one-use stateful `ClanController`;
- makes generation selection/mutation one pure deterministic operation in stable member
  order;
- prevents paused early reporters from re-entering before the complete generation transition;
- separates pure cohort/session state from Ray runtime effects;
- scopes runtime registry identity by Tune experiment and trial;
- documents the one-process-per-member Lightning topology as logical rather than physical;
- replaces serialized Lightning checkpoint editing with explicit userspace genome
  application in `on_train_start()` after optimizer restore; and
- makes Ray/Lightning/PyTorch ordinary runtime dependencies of the usable package.

## Current qualification

The corrected CPU path is directly qualified by GitHub Actions run `31849703451`.

The real Ray contract ran with:

- Python 3.11.15;
- Ray 2.57.0;
- Lightning 2.6.5;
- PyTorch 2.10.0+cpu;
- Linux;
- one CPU node; and
- two concurrently live Clan members.

All four real framework contracts passed: repeated single-parent generation transition,
fresh-runtime `Tuner.restore` after a deliberate post-restore failure, logical external
Lightning topology, and a real two-rank framework-managed DDP world. The repeated-transition
contract also preserves the accepted seed-7 sibling learning rates.

The non-Ray validation jobs passed on Python 3.11 and 3.13. They include Ruff lint/format,
wheel/sdist installation metadata and import checks, package surface checks, pure cohort
contracts, and pure evolution contracts.

The package dependency range is intentionally broader than this evidence: currently
`ray[tune]>=2.56,<3`, `lightning>=2.6,<3`, and `torch>=2.10,<3`. That range avoids needless
minor-version installation breakage; it is not a claim that every admitted version has been
qualified. Ray 2.57.0 is the current directly established scheduler compatibility point.

## Deliberate support limits

The complete Clan must fit concurrently. The current path does not yet claim:

- CUDA/NCCL;
- physical multi-node execution;
- bounded recovery after a participant disappears inside an active collective;
- custom/sharded checkpoint plugins;
- arbitrary user-supplied distributed validation samplers;
- model-sharded Clan execution; or
- realistic scientific/performance overhead.

Function-trainable actor reuse is not a current target. Restart cost should be measured
before reopening the accepted function API.

## Remaining production/adoption gates

The corrected CPU mechanics/lifecycle path is qualified, but that is not a production-ready
claim. Remaining work includes:

- GPU/multi-node/failure evidence for any corresponding support claim;
- realistic generation-boundary, checkpoint, restart, throughput, and scaling measurements;
- Clan-specific diagnostics for cohort/round/parent/mutation/checkpoint/failure events;
- a maintained static typing/PEP 561 policy if typing is claimed as supported API;
- a project-owner license decision;
- security reporting and release/version policy; and
- a real release/distribution process.

CI workflow expansion remains separately approved work and was not modified by this branch.
