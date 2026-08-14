# Active corrective and production plan

Status: correction wave qualified; production qualification continues

## Corrective baseline

The architecture correction is implemented and directly qualified on the initial two-member
single-node CPU path. The public userspace API was preserved while the internal ownership was
simplified:

- the scheduler owns the small synchronous Clan transition instead of inheriting Ray PBT
  internals;
- low-level Tune checkpoint/config transfer is isolated in `ray_compat.py`;
- generation selection/mutation is framework-independent and stable by member ID;
- the obsolete stateful worker controller is gone;
- pure cohort state is separate from Ray runtime effects;
- userspace applies the receiving genome after Lightning optimizer restoration; and
- package dependencies avoid a needless Ray minor-version pin.

GitHub Actions run `31849703451` re-established repeated generation transition, fresh-runtime
restore, logical Lightning topology, and real two-rank DDP on Ray 2.57.0 / Lightning 2.6.5 /
PyTorch 2.10.0+cpu. Passing that mechanics/lifecycle gate does not itself establish production
readiness.

## Next production work

### Complete-cohort and failure behavior

Keep the explicit requirement that the complete Clan fit concurrently. Qualify insufficient
capacity and participant failure with the current Ray/Lightning/PyTorch lifecycle before
considering extra admission/watchdog machinery. Do not build a second resource scheduler
without evidence that it materially improves the overall design.

### Compatibility

Maintain a reasonable minimum Ray/Lightning/PyTorch installation envelope and test
representative versions as the project matures. Do not point-pin users merely to avoid
maintaining the compatibility seam. Narrow dependency bounds only when direct evidence shows
an incompatible version that cannot reasonably be adapted.

### GPU and multi-node

Run the same public path on CUDA/NCCL, then across physical nodes. Resolve only gaps shown by
those environments. Revisit the logical one-process-node topology if physical-node semantics
become relevant.

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
claim. Continue testing a built wheel rather than only editable-checkout behavior.

### Release/adoption

The project owner must select a license before an ordinary open-source production release.
Add security reporting, release/version policy, and a reproducible release process
appropriate to the intended support level.

## Completion boundary

Production readiness requires the corrected architecture plus the relevant
hardware/failure/performance/release evidence. “It runs” and “all tests pass” remain inputs to
the final design review rather than its conclusion.
