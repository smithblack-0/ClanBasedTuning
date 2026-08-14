# ClanBasedTuning project status

Last updated: 2026-08-14

## Current corrective branch

The draft function-API branch is being refactored from a working mechanics implementation
into the architecture intended for continued maintenance.

The public user shape remains unchanged:

- ordinary Ray Tune function trainable receiving the current genome/config;
- `ClanScheduler` through `TuneConfig(scheduler=...)`;
- `ClanDDPStrategy` through Lightning's strategy interface;
- `ClanTuneReportCallback` through Lightning callbacks; and
- one Ray trial/resource allocation per Clan member.

Genome application remains entirely userspace.

## Architecture correction

The corrective implementation removes inheritance from Ray's stock PBT internals. The
scheduler now owns the small synchronous Clan transition itself and isolates unavoidable
Tune checkpoint/config transfer details in `ray_compat.py`. This avoids tying package users
to one Ray minor release merely to preserve PBT subclass internals.

The same wave also:

- removes the one-use stateful `ClanController`;
- makes generation selection/mutation one pure deterministic operation in stable member
  order;
- separates pure cohort/session state from Ray runtime effects;
- scopes runtime registry identity by Tune experiment and trial;
- documents the one-process-per-member Lightning topology as logical rather than physical;
- replaces serialized Lightning checkpoint editing with explicit userspace genome
  application in `on_train_start()` after optimizer restore; and
- makes Ray/Lightning/PyTorch ordinary runtime dependencies of the usable package.

## Qualification state

Before this correction, the two-member CPU path had direct evidence for repeated generation
transition and fresh-runtime `Tuner.restore` with Ray 2.56.x, Lightning 2.6.x, PyTorch 2.10.x,
and Python 3.11.

Because scheduler state-transfer implementation changed materially, that evidence must be
re-established on the exact corrective branch head. Until the real Ray framework-contract
job is green, the branch is a qualification target rather than a newly qualified release.

## Deliberate support limits

The current product direction still requires the complete Clan to be runnable concurrently.
It does not yet claim CUDA/NCCL, multi-node execution, bounded recovery after a participant
disappears inside an active collective, custom/sharded checkpoint plugins, arbitrary
user-supplied distributed validation samplers, model-sharded Clan execution, or realistic
scientific/performance overhead.

Function-trainable actor reuse is not a current target. Restart cost should be measured
before reopening the accepted function API.

## Repository readiness

Packaging, documentation, examples, tests, and architecture are being corrected together.
Remaining production/adoption gates include:

- exact-head Ray/Lightning/PyTorch framework qualification after this refactor;
- GPU/multi-node/failure evidence for any corresponding support claim;
- realistic performance/overhead measurements;
- Clan-specific diagnostics;
- a maintained typing policy if static typing is claimed;
- a project-owner license decision;
- security reporting and release/version policy; and
- a real release/distribution process.

CI workflow expansion remains separately approved work and is not modified by this branch.
