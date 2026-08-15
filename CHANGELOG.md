# Changelog

Notable user-visible changes are recorded here. The project is pre-1.0; compatibility impact
is called out explicitly when a release is prepared.

## Unreleased

### Added

- Executable tiny MLP/AdamW qualification workload for the complete Clan function path.
- Local two-GPU CUDA/NCCL, physical multi-node, insufficient-capacity, and opt-in destructive
  peer-failure qualification surfaces.
- Standard Clan lifecycle diagnostics.
- PEP 561 typing marker and maintained package-source static type check.
- Tiny no-download performance measurement harness.
- Security, release, hardware, performance, and final quality-audit readiness procedures.
- Pure injected runtime registration/release contracts.

### Changed

- Distribution qualification now validates typed-package metadata and release artifact
  rendering in addition to non-editable wheel import behavior.
- Scheduler runtime registration is injected/cached instead of issuing repeated construction
  work from scheduling callbacks.
- Successful experiments release their registry assignments and cohort-specific coordinator.
- Timed-out pre-DDP members retract pending rendezvous state so later members cannot enter DDP
  with a dead peer.
- Operational composition points expose explicit testing/injection seams instead of requiring
  patching.
