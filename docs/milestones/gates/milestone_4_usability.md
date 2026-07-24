# Milestone 4 gates — usability

Status: proposed completion gates  
Date: 2026-07-24

## Milestone result

A Lightning user can attach ClanBasedTuning through a short, documented
construction path without manually assembling the surrounding DDP, model, data,
and plugin lifecycle.

## Gates

### M4.1 The ideal user path is designed before the frontend is fixed

- The intended user sequence is written and reviewed before its manufacturing
  API becomes contractual.
- User-owned choices remain with Lightning, Ray Tune, PyTorch, and the user's
  model rather than being absorbed into a package configuration language.

### M4.2 The construction path returns concrete framework components

- The frontend returns the concrete Lightning strategies, plugins, callbacks,
  samplers, or other objects the caller supplies to native framework entry
  points.
- It does not return another factory, own a Trainer, or create a parallel launch
  system.

### M4.3 DDP, model, data, and rendezvous setup are package-managed

- The simple path configures the accepted DDP behavior, model wrapping, rank and
  rendezvous information, training partitioning, comparable evaluation, and
  member-local checkpoint behavior.
- Invalid population or resource composition fails before training begins.

### M4.4 Convenience remains auditable composition

- Each convenience operation delegates to the same lower-level primitives proven
  in Milestone 3.
- The manual path remains documented and usable for advanced integration.
- No convenience-only implementation diverges from the composable path.

### M4.5 The supported user envelope is explicit

- Supported Lightning, Ray, PyTorch, topology, loader, precision, optimizer, and
  stopping assumptions are stated in user-facing documentation.
- Unsupported configurations fail clearly rather than silently degrading Clan
  semantics.

### M4.6 Documentation and examples are sufficient for a new user

- A user guide explains the short construction path, required framework setup,
  lifecycle, limitations, and failure messages.
- A complete example runs through the supported round lifecycle without hidden
  manual setup.
- Documentation agrees with the public implementation.

## Assigned deferrals

| Capability | Destination | Why not required here | Destination obligation | Required evidence |
| --- | --- | --- | --- | --- |
| General optimizer resolution | Milestone 5 | The usability path may support the narrow optimizer contract already proven. | Make evolved configuration application predictable across realistic layouts. | Utility tests and reference docs. |
| Production-scale observability, sharding, and cluster recovery | Milestone 6 | The simple path is qualified for its declared non-industry envelope. | Qualify serious operating environments and failure modes. | Industry readiness audit. |
