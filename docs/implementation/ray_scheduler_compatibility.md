# Ray scheduler compatibility boundary

Status: corrective implementation decision

## Problem

Clan Tuning needs a synchronous population transition that Ray Tune does not expose as one
stable public operation:

1. wait for every trial at one boundary;
2. choose one parent;
3. capture that parent's just-reported checkpoint;
4. pause every member;
5. replace every member's config; and
6. make every member resume from the same parent checkpoint.

Ray's Population Based Training implementation already proves that Tune can perform these
operations, but PBT itself uses internal scheduler state and private/Developer Tune machinery.
Subclassing PBT therefore couples CBT simultaneously to PBT's internal algorithm layout and
to the lower-level Tune transfer operations.

## Decision

CBT owns the small synchronous Clan scheduler algorithm directly as a `FIFOScheduler`
specialization. It does not vendor the full general-purpose PBT implementation and does not
inherit PBT's private `_quantiles`, `_trial_state`, `_checkpoint_or_exploit`, mutation, or
asynchronous machinery.

The current implementation was behaviorally derived from Ray synchronous PBT because that is
the upstream reference for checkpoint/pause/config transfer. CBT keeps only the operations
needed by Clan Tuning.

## Compatibility adapter

`src/clan_based_tuning/ray_compat.py` is the sole intended location for Tune implementation
details beneath the scheduler callback API. It currently owns:

- scheduling/resolving the selected trial checkpoint at the current report boundary;
- pausing a trial without requesting an extra checkpoint; and
- assigning a child config plus inherited checkpoint into the state Tune uses on resume.

These operations use Ray Developer/private APIs because Tune does not provide a stable public
atomic alternative. No selection, mutation, cohort, Lightning, or user policy belongs in the
adapter.

## Version policy

Ray's stable `PublicAPI` receives a strong backward-compatibility commitment; `DeveloperAPI`
may change across minor releases. `TrialScheduler`/`Trial` are Developer APIs, so CBT cannot
claim that an arbitrary future Ray minor is guaranteed compatible.

That does not justify point/minor pinning every user to the exact version used while this code
was written. Historically the Tune scheduler lifecycle has changed slowly, and isolating the
few lower-level operations gives the project a small repair surface when Ray changes.

Package metadata therefore expresses a reasonable major-version envelope rather than
`ray==2.56.x` or `<2.57`. Actual support is established by representative compatibility tests.
If an upstream version breaks `ray_compat.py`, the preferred response is to adapt that module
and rerun framework qualification; dependency bounds are narrowed only when no reasonable
compatible implementation exists.

## Why not copy all of PBT?

A verbatim PBT copy would freeze substantial behavior CBT does not need: asynchronous mode,
quantile fractions, arbitrary parent sampling, Ray mutation/resampling formats, logging
formats, and several PBT-specific state paths. It would also still contain the same private
Tune transfer operations that can change upstream.

Reducing the implementation to the Clan-specific synchronous algorithm improves auditability
and leaves one explicit compatibility seam instead of silently inheriting a much larger
upstream subsystem.

## Qualification requirement

Any change to scheduler transition logic or `ray_compat.py` requires the real Ray framework
contracts: repeated two-member continuation, child mutation, selected checkpoint transfer,
and fresh-runtime `Tuner.restore`. A green pure unit suite is not evidence that these
Developer/private Tune interactions remain compatible.
