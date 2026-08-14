# Changelog

Notable user-visible changes are recorded here. The project is pre-1.0; compatibility impact
is called out explicitly when a release is prepared.

## Unreleased

### Added

- Executable tiny MLP/AdamW qualification workload for the complete Clan function path.
- Local two-GPU CUDA/NCCL, physical multi-node, bounded-capacity, and opt-in destructive
  peer-failure qualification surfaces.
- Standard Clan lifecycle diagnostics.
- PEP 561 typing marker and maintained package-source static type check.
- Tiny no-download performance measurement harness.
- Security, release, hardware, performance, and final quality-audit readiness procedures.

### Changed

- Distribution qualification now validates typed-package metadata and release artifact
  rendering in addition to non-editable wheel import behavior.
