# ClanBasedTuning project status

Last updated: 2026-08-14

## Current readiness branch

Merged PR #52 remains the corrected function-API baseline. The readiness branch adds
qualification, diagnostics, typing/distribution checks, release process, and the final
repository quality audit without changing the accepted public three-object API or moving
genome application out of userspace.

The executable readiness/audit candidate is commit
`8f4e07ea93c8d4525920212f93c365cfd148e1e7`. GitHub Actions run `31852871160` passed both
ordinary Python validation jobs and the real Ray/Lightning framework job on that exact commit.

## Directly established CPU behavior

The real framework job used Python 3.11.15, Ray 2.57.0, Lightning 2.6.5, PyTorch 2.10.0+cpu,
Linux, and local CPU execution. It passed:

- repeated two-member single-parent Clan generation transition;
- fresh-runtime `Tuner.restore` after a deliberate post-restore failure;
- insufficient-capacity failure at the CBT rendezvous boundary before DDP;
- a realistic tiny two-layer MLP + AdamW repeated training/restore contract;
- logical one-process-member Lightning topology; and
- a real two-rank framework-managed GLOO DDP world.

The insufficient-capacity contract gives Ray only one CPU for a two-member Clan. Both trials
must fail with the CBT `complete Clan did not become resident` rendezvous error and neither may
reach a `DistNetworkError`. Timed-out pre-DDP announcements are retracted before failure so a
later process cannot rendezvous with a dead member.

The ordinary validation jobs passed on Python 3.11 and 3.13. They include Ruff lint/format,
package-source mypy, wheel/sdist build and `twine check`, non-editable installed-wheel import,
package-surface checks, pure cohort/runtime/evolution contracts, and the remaining non-Ray
suite.

## Dependency and compatibility policy

The package dependency envelope remains intentionally broader than the directly tested
configuration:

- `ray[tune]>=2.56,<3`;
- `lightning>=2.6,<3`; and
- `torch>=2.10,<3`.

These are compatibility/installability bounds, not a claim that every admitted version has
been qualified. Ray-specific low-level continuation transfer remains isolated in
`ray_compat.py`; framework-minor changes should be repaired at that boundary when possible
rather than forcing users onto one point release.

## Repository quality audit

The mandatory post-gate repository-wide audit is recorded in
[`docs/reviews/readiness_quality_audit.md`](docs/reviews/readiness_quality_audit.md). It reviewed
shipped source, tests, examples, active docs, packaging, qualification, and release surfaces
against the project style/quality contract after the readiness work was synchronized.

Concrete audit findings were fixed before the audit passed, including runtime-construction
ownership, repeated Ray registration work, completed-runtime cleanup, stale pre-DDP
rendezvous state, auxiliary-function injection seams, and documentation/module-organization
gaps. Passing tests were treated as evidence for the review rather than as the review itself.

## Runnable but not yet qualified locally

The repository contains no-download/local qualification harnesses for remaining environment-
dependent claims:

- two-GPU CUDA/NCCL;
- physical multi-node Ray execution with shared Tune storage; and
- destructive live-DDP-participant failure.

A skip is not evidence. These support claims remain open until the corresponding test passes
on a named environment and that evidence is recorded.

The CUDA/NCCL test can be run from a checkout with:

```bash
python -m pip install -e '.[dev]'
python -m pytest tests/hardware/test_cuda_function_path.py -vv
```

It uses only the tiny synthetic MLP/AdamW workload; no model or dataset download is required.
Physical multi-node and destructive-failure setup are documented in
[`docs/qualification/hardware.md`](docs/qualification/hardware.md).

## Remaining external release gates

The repository engineering/readiness audit is complete, but an ordinary production/public
release is still blocked by evidence or owner decisions outside this CPU qualification run:

- **License:** the project owner must choose the license; this branch does not make that legal
  decision.
- **CUDA/NCCL:** test exists but has not been run on two visible GPUs in recorded evidence.
- **Physical multi-node:** test exists but has not been run against a recorded two-node cluster.
- **Active-collective participant failure:** destructive harness exists but has not been run in
  recorded evidence.
- **Performance:** reproducible measurement tooling exists, but representative workload/hardware
  measurements are still required before making overhead or scaling claims.
- **Model sharding/custom checkpoint plugins:** remain unqualified and are not current support
  claims.

CI workflow expansion remains separately approved work and was not modified by this branch.
