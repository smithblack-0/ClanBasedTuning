# Framework-native integration review

Status: complete for the qualified CPU function path
Date: 2026-08-14

## Review question

Does ClanBasedTuning own only the coordination that the upstream frameworks cannot already
provide, while leaving execution, resources, distributed mechanics, optimizer restoration,
and genome application with their natural owners?

For the qualified CPU function path, yes.

## Framework ownership retained

Ray Tune still owns trial creation, per-trial resources, pause/resume execution, checkpoint
storage, result handling, and experiment restoration. CBT supplies a Tune scheduler but does
not create a second trial executor or resource scheduler.

Lightning/PyTorch still own the Trainer lifecycle, optimizer restoration, backend selection,
process-group initialization, DDP gradient synchronization, barriers, and checkpoint
construction. CBT supplies topology facts Lightning cannot infer from independently launched
Tune trials and scopes which member persists the round continuation.

User code still owns the Tune config/genome meaning and applies it to the restored optimizer.
CBT does not infer optimizer mappings, provide an `apply_genome` callback, edit Lightning's
serialized optimizer payload, or own a package-side optimizer schema.

## Clan-owned behavior

The scheduler owns only the synchronous Clan population transition: wait for one boundary
report from every stable member, select one parent, capture its checkpoint, construct one
independently mutated child config per member, and assign those continuations before the next
generation resumes.

The pure evolution module owns selection/mutation arithmetic. The pure cohort module owns
experiment-scoped identity and invocation rendezvous state. The Ray runtime module owns actor,
Tune-context, socket, timeout, registration, and release effects. These concerns no longer
collapse into one operational scheduler object.

## Runtime construction and lifecycle

The final readiness audit found that runtime actor registration was still being reached as
scheduler-owned construction and was repeated on scheduling callbacks. That was corrected.

`ClanScheduler` now receives runtime registration/release operations through explicit
injection. `runtime.py` constructs or reuses the named registry/coordinator, performs the Ray
registration calls, and releases successful completed assignments. Scheduler state only holds
opaque handles while live and strips them before serialization.

The shared registry removes completed experiment/trial assignments and the scheduler-owned
coordinator is terminated after the full successful population completes. A timed-out pre-DDP
member retracts its exact pending rendezvous token before raising, preventing later members
from constructing DDP state with a dead peer.

## Tune compatibility boundary

Tune exposes scheduler lifecycle hooks but not a public atomic operation equivalent to
"resume this trial with that trial's checkpoint and this new config." The small unsupported
transfer seam therefore remains isolated in `ray_compat.py`.

This is preferable to inheriting all of PBT's private policy internals or copying a second Tune
executor. The dependency metadata consequently uses broad major-version bounds; direct
framework tests determine support and a future Tune change should normally require one
compatibility-adapter repair.

## DDP topology

One Tune member is one independently launched Lightning process/device. CBT presents each as a
logical one-process node so Lightning can preserve the externally assigned global rank/world
size without spawning another local process. This is adapter bookkeeping, not a physical-node
claim.

Training retains normal DDP partitioning. Lightning-managed validation is replicated for
candidate comparability. Explicit user-supplied distributed samplers remain user-owned.

## Failure ownership

Pre-DDP complete-cohort failure is bounded and diagnosed by CBT because CBT owns the
cross-trial rendezvous facts. Once PyTorch DDP is active, collective/backend failure remains
framework-owned. The repository contains a destructive peer-exit qualification harness, but
transparent active-collective recovery is not claimed.

## Review result

No second scheduler, optimizer manager, checkpoint format, process group, or execution runtime
was introduced. The remaining private Ray dependency is narrow and explicitly qualified.
This framework-ownership result is also included in the final repository quality audit.
