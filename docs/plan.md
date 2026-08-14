# Active corrective and production plan

Status: current implementation sequence

## Current objective

Turn the qualified CPU mechanics prototype into a maintainable package without changing the
accepted userspace API or taking over framework responsibilities. The present correction
wave addresses architecture and testability first; hardware/performance/release evidence
follows after that shape passes exact-head framework qualification.

## Correction wave

The current branch should leave the repository with these properties:

1. `ClanScheduler` owns the small synchronous Clan transition directly rather than relying
   on Ray PBT private subclass hooks.
2. All remaining low-level Tune checkpoint/config transfer operations live in one documented
   compatibility module; Ray is not point/minor pinned merely to freeze PBT internals.
3. Selection and sibling mutation are framework-independent, deterministic in stable member
   order, and shared by worker/scheduler paths.
4. The obsolete stateful worker `ClanController` is removed; the callback performs one
   gather followed by the shared pure selection rule.
5. Pure cohort/session state is separated from Ray actor/socket/Tune-context effects, and
   registry lookup is experiment-scoped.
6. Logical Lightning topology is documented explicitly instead of presenting logical
   member-as-node rank as physical-node identity.
7. Userspace applies the current genome after Lightning optimizer restoration through a
   user-owned lifecycle hook; examples no longer edit Lightning checkpoint internals.
8. Ray/Lightning/PyTorch are normal runtime dependencies because the public package is an
   integration product, and the package exports its real public classes directly.
9. Unit/framework/distribution tests describe durable behavior rather than historical source
   shape or removed APIs.
10. Active README/API/design/qualification/status documents agree with the corrected code.

The branch remains draft until the real Ray framework contracts are green at its exact head.
No CI workflow change is part of this wave.

## Production qualification after correction

### Complete-cohort and failure behavior

Keep the explicit requirement that the complete Clan fit concurrently. Qualify insufficient
capacity and participant failure with the current Ray/Lightning/PyTorch lifecycle before
considering any extra admission/watchdog machinery. Do not build a second resource scheduler
without evidence that it materially improves the overall design.

### Compatibility

Maintain a reasonable minimum Ray/Lightning/PyTorch support envelope and test representative
versions as the project matures. Narrow dependency bounds only when an actual incompatibility
is found. A Ray change should normally require at most a `ray_compat.py` repair.

### GPU and multi-node

Run the same public path on CUDA/NCCL, then across nodes. Resolve only gaps demonstrated by
those environments. The logical one-process-node topology must be revisited if physical-node
semantics become relevant.

### Realistic application and performance

Add a small realistic optimizer-training E2E and measure generation-boundary overhead,
checkpoint cost, function-process restart cost, and throughput relative to ordinary DDP.
Actor reuse or another user API should be reconsidered only if measurements show the current
function path is materially too expensive.

### Observability

Add Clan-specific diagnostics for cohort formation, generation boundary, selected parent,
child mutations, checkpoint transfer, and failure while avoiding duplicate framework logs.

### Typing and distribution

Finish trustworthy annotations and decide on a maintained static-checker/PEP 561 support
claim. Continue testing a built wheel rather than only editable checkout behavior.

### Release/adoption

The project owner must select a license before an ordinary open-source production release.
Add security reporting, release/version policy, and changelog/release automation appropriate
to the intended support level. These are adoption gates, not substitutes for architecture or
runtime qualification.

## Completion boundary

A production claim requires the corrected architecture to survive its exact framework tests
and the relevant hardware/failure/performance evidence. “It runs” and “all tests pass” remain
inputs to the final design review rather than its conclusion.
