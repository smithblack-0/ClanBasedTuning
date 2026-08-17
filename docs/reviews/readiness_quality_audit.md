# Readiness style and quality audit

Status: PASS for repository engineering/style quality; external release evidence remains open
Date: 2026-08-15
Executable commit: `5f117df15b89d468663abdb6ec9e316ca89ca2b8`
Executable workflow: `31902897008`

## Scope

This is the mandatory final gate after CPU/failure qualification, hardware harnesses,
diagnostics, typing/distribution, performance tooling, security/release process, and
README/API/example synchronization were in place.

The audit reviewed shipped package source, unit/framework/hardware tests, test support code,
the runnable example, benchmark, active README/API/status/qualification/design/release docs,
and packaging metadata against the project's authoritative style/quality contract. Passing
tests were evidence available to the review; they were not treated as proof that the design
was finished.

The audit was reopened after an initial documentation pass because function/method docstrings
had been treated too much as a coverage requirement. The corrective pass used documentation as
an abstraction diagnostic: a retained function should have non-obvious responsibility,
invariant, framework contract, failure semantics, or ownership worth preserving. If its best
docstring merely restates the signature or body, the abstraction itself is suspect.

## Problems found and corrected

### Runtime construction was still too scheduler-owned

The scheduler reached Ray registry/coordinator construction/registration and repeated that
registration during scheduling callbacks. This blurred responsibility and added unnecessary
synchronous Ray calls.

Correction: runtime construction/registration/release lives in `runtime.py` and is supplied to
`ClanScheduler` through explicit injected operations. The scheduler caches one live
registration per process and strips handles on serialization so restore reconstructs them.

### Completed Ray runtime state was not released

The shared registry retained completed experiment assignments and cohort-specific named actors
had no successful-run cleanup path. That is harmless in short tests but poor behavior in a
long-lived Ray cluster.

Correction: successful completion of the whole population removes experiment-scoped registry
entries and terminates only the scheduler-owned coordinator. Error state is not eagerly
destroyed because Ray retry/restore remains the owner of whether the experiment continues.

### Insufficient-capacity failure could leave a dead rendezvous peer

The first one-CPU member correctly reached CBT's complete-cohort timeout, but its pending
announcement remained. A later member could form a DDP session using that dead process's
address/port and fail later in PyTorch networking instead of at the CBT boundary.

Correction: a process that abandons pre-DDP rendezvous retracts its exact token before raising.
The real one-CPU contract now requires both trials to fail with CBT's complete-Clan rendezvous
error and rejects `DistNetworkError`.

### Function composition was not fully injectable

Several operational composition points still called project helpers directly even though the
quality contract requires auxiliary dependencies to be overridable where isolation matters.

Correction: generation winner policy, callback winner policy, scheduler generation/transfer
operations, runtime registration/release, runtime discovery helpers, and Ray checkpoint-result
resolution have explicit injection seams. Unit tests use those seams rather than patching.

### Documentation coverage had concealed weak abstractions

The initial documentation cleanup could produce a formally documented method without answering
why the method existed. That made trivial wrappers look healthier than they were and encouraged
maintenance prose that simply narrated implementation.

Correction: the second pass required every retained production function/method to earn its
boundary. Trivial single-use wrappers such as mutation-rule construction, scheduler null-check
helpers, runtime member lookup indirection, a timeout wrapper, and benchmark argument parsing
were folded back into their callers. Small framework-required methods remained when the
framework interface itself justified the boundary; their documentation now explains the
framework contract or unusual rank/topology semantics instead of restating the return value.

The same pass removed redundant or unjustified state exposed by trying to document it:
`TuneMemberEnvironment` no longer accepts caller-supplied local/node ranks that CBT's supported
logical topology already determines, rendezvous sessions no longer carry an unused session id,
and non-rank-zero members no longer retain unused host identity.

The repository's engineering workflow and contributing contract now state the forcing-function
rule explicitly: if a function's useful documentation can only paraphrase its name, signature,
or obvious body, reconsider whether the function should exist. This is a review principle, not
a mechanical docstring-quality linter.

### Tests still froze harmless source shape

Package and built-wheel contracts asserted one exact ordering of `__all__`. That protected an
implementation presentation detail rather than the public API.

Correction: package/distribution tests now require the exact public export set without coupling
qualification to arbitrary ordering. Test documentation was also tightened around durable
behavior and why subprocess/framework boundaries are being exercised.

## Quality-contract result

### Fast

PASS for current scope. The audit removed repeated runtime-registration RPCs from scheduler
callbacks and avoids a second scheduler/process group/optimizer manager. A reproducible tiny
benchmark exists for measuring real control-plane cost. Representative model/hardware
performance evidence is still an explicit external gate, so no throughput claim is made.

### Effective

PASS for the directly qualified CPU problem. Clan generation policy is a small pure operation;
Ray owns trials/resources/storage; Lightning/PyTorch own training and DDP. Real framework
contracts cover repeated transition, restore, comparable validation, common gradients,
realistic MLP/AdamW training, and insufficient-capacity failure at the intended boundary.

### Maintainable

PASS. Pure evolution and cohort state are separated from framework effects. Unavoidable Tune
private transfer operations are isolated in `ray_compat.py`. Runtime construction/lifecycle is
externalized and injectable. Function/method documentation now records knowledge a maintainer
would otherwise lose, while abstractions that could not justify such knowledge were removed
rather than padded with ceremonial docstrings.

### Correct

PASS for the stated CPU support boundary. Workflow `31902897008` passed Python 3.11, Python
3.13, and the real Ray/Lightning contract on executable commit
`5f117df15b89d468663abdb6ec9e316ca89ca2b8`. Userspace genome application remains visible
after optimizer restoration, worker/driver winner decisions are cross-checked, sibling
mutation semantics are retained, and partial capacity cannot silently enter DDP.

### Concise

PASS. The repository does not vendor PBT, add a Trainable wrapper, create a package optimizer
schema, own a second distributed backend, or add a separate telemetry runtime. The abstraction
pass also removed small wrappers and redundant state that had no independent maintenance role.
Added readiness surfaces reuse one tiny workload across CPU, GPU, multi-node, failure, and
performance qualification instead of duplicating large fixtures.

## Construction and framework exception review

Framework-facing public adapters (`ClanScheduler`, `ClanDDPStrategy`, and
`ClanTuneReportCallback`) remain directly instantiated because Ray/Lightning APIs consume
those concrete objects and the accepted public API is intentionally three objects. A redundant
public factory layer would add surface without hiding any useful construction complexity.

Project-owned dependency construction inside those adapters was nevertheless reviewed under
the stricter construction rule: runtime actors/specs, Lightning environment construction,
mutation-rule construction, policy/transfer helpers, and other isolatable dependencies are
externalized or injected where the seam buys meaningful isolation. The direct framework
constructors therefore hold configuration and framework subclass state, not a hidden internal
object graph.

## Test review

PASS. Pure unit tests exercise evolution, cohort, and runtime construction/lifecycle through
injection rather than patching. Real Ray/Lightning/PyTorch contracts exercise the framework
boundaries. The realistic tiny MLP/AdamW contract prevents the suite from relying only on a
one-parameter scalar model. Distribution tests exercise built artifacts and non-editable
imports without freezing irrelevant export ordering.

Hardware/topology tests are deliberately self-skipping when their required environment is
absent. Those skips remain non-evidence.

## Documentation and example review

PASS for synchronization and maintenance value. README, API docs, runnable example, STATUS,
qualification records, framework-native review, release policy, security policy, changelog,
benchmark instructions, and local hardware commands agree on the same public API and evidence
boundary. Userspace optimizer application is explicit in both the example and primary docs.
Production function/method documentation is no longer accepted merely because it exists; it
must explain a boundary worth keeping.

## Packaging and dependency review

PASS for repository readiness. The package ships `py.typed`, runs a maintained package-source
mypy check, builds wheel and sdist, passes `twine check`, installs the wheel non-editably, and
imports the public objects from that artifact.

Framework dependencies use major-version compatibility bounds rather than a point Ray pin.
Direct support evidence remains Ray 2.57.0 / Lightning 2.6.5 / PyTorch 2.10.0+cpu for this
candidate; metadata does not pretend every admitted minor combination was tested.

## External gates that this audit cannot pass by inspection

The repository engineering/style audit does **not** convert unrun or owner-dependent gates
into support claims. The following remain open:

- owner selection of project license terms;
- recorded two-GPU CUDA/NCCL qualification;
- recorded physical multi-node qualification with shared Tune storage;
- recorded destructive live-participant failure qualification;
- representative workload/hardware performance and scaling measurements; and
- any future model-sharded/custom-checkpoint support claim.

The repository contains executable procedures for the environment-dependent evidence items
where software can provide them. Until those records exist, STATUS and release notes must
continue to present them as non-claims/blockers.
