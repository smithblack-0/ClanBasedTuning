# ClanBasedTuning project status

Last updated: 2026-08-14

## Current branch

The corrected function API from merged PR #52 is the baseline. The current readiness branch
adds executable qualification surfaces around that architecture without changing the public
three-object API or taking genome application out of userspace.

## Directly established baseline

The merged CPU path is directly qualified on Python 3.11.15, Ray 2.57.0, Lightning 2.6.5,
PyTorch 2.10.0+cpu, Linux, one node, and two concurrent members. The merged contracts establish
repeated single-parent generation transition, fresh-runtime `Tuner.restore`, logical external
Lightning topology, and a real two-rank framework-managed DDP world.

The dependency envelope remains deliberately broader than that evidence:
`ray[tune]>=2.56,<3`, `lightning>=2.6,<3`, and `torch>=2.10,<3`. Those bounds avoid needless
minor-version installation failures; they are not a blanket qualification claim.

## Readiness work on this branch

The repository now includes:

- a small realistic MLP + AdamW CPU framework contract in addition to the scalar mechanics
  contract;
- a bounded insufficient-capacity failure contract;
- an opt-in destructive live-peer failure contract;
- a two-GPU CUDA/NCCL contract that self-skips without two visible GPUs;
- an opt-in physical multi-node contract requiring shared Tune storage and distinct nodes;
- standard Python diagnostics for cohort registration/join, boundary progress, selection,
  mutation continuations, checkpoint source, and timeout failures;
- a PEP 561 marker plus maintained package-source mypy contract;
- wheel/sdist metadata/import checks and release-artifact validation;
- a no-download tiny function-path measurement harness; and
- security, release, hardware, performance, and quality-audit documentation.

A harness existing in the repository is not itself qualification. CPU/static/distribution
claims from this branch become current only when the exact branch head passes its normal
checks. CUDA/NCCL, physical multi-node, and destructive active-peer behavior remain non-claims
until their opt-in contracts are run in the required environment and the evidence is recorded.

## Release blockers and non-claims

The following remain external or evidence-dependent gates:

- **License:** blocked on the project owner's legal/license choice. No license is selected by
  this branch.
- **CUDA/NCCL:** locally runnable, but not claimed until the two-GPU contract passes on named
  hardware/software.
- **Physical multi-node:** locally runnable against a configured Ray cluster with shared
  storage, but not claimed until direct evidence exists.
- **Active-collective participant failure:** destructive harness exists; bounded behavior is
  not claimed until it passes in the intended environment.
- **Performance:** measurement tooling exists; representative throughput/overhead/scaling data
  must be recorded before making performance claims or reopening actor reuse.
- **Model sharding/custom checkpoint plugins:** not qualified.

## Completion rule

Production/readiness work does not end when tests turn green. After executable gates and
active docs/examples are synchronized, the mandatory final gate is a repository-wide audit
against the authoritative style and quality contract. Any concrete issue found there is fixed
before the audit can pass.

CI workflow expansion remains separately approved work and is not modified by this branch.
