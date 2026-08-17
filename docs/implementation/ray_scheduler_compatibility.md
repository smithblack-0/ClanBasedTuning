# Ray scheduler compatibility

## Problem

Clan Tuning needs a synchronous complete-population transition: all members report one common
boundary, one parent is selected, and every member resumes from that parent's checkpoint with
an independently mutated sibling config.

Ray Tune exposes scheduler lifecycle hooks for controlling trial decisions, but the atomic
checkpoint/config replacement used by PBT is not a stable public operation. Inheriting the
full PBT implementation would couple Clan semantics to unrelated private policy internals.

## Current boundary

`ClanScheduler` therefore subclasses Tune's FIFO scheduler surface and owns only the small
Clan-specific synchronous transition. Pure winner/mutation logic lives in `evolution.py`.

The unavoidable low-level Tune transfer operations are isolated in `ray_compat.py`:

- obtain/resolve the selected boundary checkpoint;
- pause a member without requesting a duplicate checkpoint; and
- assign a receiving member's child config and selected checkpoint continuation.

Ray-specific actor construction is not part of the scheduler. `runtime.py` constructs/reuses
registry and coordinator actors and exposes injected registration/release operations to the
scheduler.

## Generation scheduling invariant

Once any member reports a boundary, `ClanScheduler.choose_trial_to_run` returns no paused
member until every current member has reported and the population transition completes. This
prevents an early reporter from starting the next invocation while another member is still in
the previous generation.

Every sibling mutation is generated from one snapshotted parent config in stable member-ID
order. The previous winner is mutated too.

## Runtime registration and cleanup

A complete Tune population is registered once per live scheduler process. Repeated scheduling
callbacks reuse the already-live handles rather than performing synchronous Ray registration
round-trips every time.

The scheduler excludes actor handles from serialized state. Restore reconstructs and
re-registers them through the runtime construction layer.

After every member of a successful population completes, the experiment-scoped registry
entries are removed and the cohort-specific coordinator actor is terminated. Errored runs are
not eagerly destroyed because Ray retry/restore policy remains the owner of whether they
continue.

During pre-DDP rendezvous, a member that reaches the configured complete-cohort timeout
retracts its exact pending announcement before raising. A later member therefore cannot open a
session using that dead process's address/port.

## Dependency policy

Package metadata admits `ray[tune]>=2.56,<3` rather than pinning one minor release. This is a
compatibility envelope, not a blanket qualification claim. The exact readiness candidate was
directly exercised with Ray 2.57.0.

If a future Ray minor changes the low-level transfer operations, repair `ray_compat.py` and
rerun framework contracts first. Narrow the dependency range only if the upstream change is
actually incompatible rather than as a substitute for maintaining the adapter.
