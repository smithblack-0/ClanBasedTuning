# Senior engineering workflow

This guide defines the standing process for serious ClanBasedTuning engineering
work. It is not a milestone checklist and does not replace the governing roadmap,
decisions, gates, accepted design, or active plan.

## Core imperative

Continuously evaluate and improve the design while implementing it. Never narrow
the job to “make the requested patches,” and never treat “runs and compiles” as
equivalent to “finished.” Every implementation and review pass must consider
whether the contract, ownership, or design itself is wrong.

Minor design corrections may be made and reported afterward. A change that
unlocks new behavior, changes scientific meaning, alters authority or recovery,
or materially expands scope must be discussed before implementation.

## Preserve the authority layers

Engineering work moves through distinct abstraction layers:

1. The roadmap defines the project capability and development sequence.
2. The milestone gate defines the complete acceptable solution space needed to
   make that capability safe and sufficient downstream.
3. An accepted design selects one solution within the gate.
4. An accepted plan may govern execution of that design within the active gate.
5. Implementation and evidence establish whether the gate is actually satisfied.

A design may narrow the gate by choosing one solution for implementation. A plan
may narrow the design into the next executable steps. Neither may narrow the
gate contract or acquire upward authority merely because it is current.

A durable plan is authoritative only inside its declared active-milestone scope.
It may encode necessities created by the accepted design and current project
state, but it may not predesign later milestones. When current work discovers a
condition that future work genuinely must satisfy, propose that condition to the
owning future gate for explicit review rather than leaving it as a forward
promise in the current plan.

Before accepting a design assumption as a requirement, ask:

- Could another materially different design satisfy the gate?
- Could the roadmap result be fully achieved without this assumption?
- Would deleting the current plan leave the gate complete?
- Can downstream work rely on the gate result without knowing this detail?
- Is this detail present only because the current implementation makes it
  convenient?

If a current route fails, revise the route or design first. Reopen a gate only
when evidence shows the acceptance envelope itself is wrong or incomplete, and
consult the user before changing it.

Do not place plans or scratch designs beside milestone gates. A durable plan,
when justified, must live in a clearly identified planning or design location,
state the active gate it serves, and stop at that gate boundary. Preserve
framework research, source observations, option fragments, tentative ideas, and
unresolved questions in [`scratchwork/`](scratchwork/README.md) when they may help
future work. Scratchwork is explicitly non-authoritative and disposable; it may
not assign work, narrow a gate, or predesign a later milestone.

## Before coding

1. Read the roadmap requirement, active milestone gate, accepted decisions,
   accepted design, active plan when one exists, current artifact, relevant
   comments, and nearby consumers. Do not reconstruct intent from names or from
   a plan outside its declared scope.
2. State the success criteria and current implementation boundary. Distinguish
   “this unit is complete” from “the active plan is complete” and from “the
   milestone gate is satisfied.”
3. Identify each proposed class or function’s main idea: why it exists, what it
   owns, and what it explicitly does not own.
4. Search across the whole relevant system for existing implementations,
   duplicated responsibilities, and remote consumers before introducing a new
   abstraction.
5. If the proposed design already looks overloaded, brittle, or unnecessary,
   redesign it before writing the first implementation.

## Implementation is iterative

Treat the first working implementation as a draft. For every completed unit,
perform these passes before calling it done.

### 1. Contract pass

- Does every class have one coherent main idea?
- Do its details directly support that idea?
- Is orchestration performing calculation, reduction, storage, or policy that
  belongs to another owner?
- Does data leave a component in the form promised by its contract?
- Does the implementation satisfy the gate without pretending its design choices
  are gate requirements?
- Does the work remain inside the active plan and gate rather than designing a
  later milestone?

### 2. DRY and boundary pass

- Search again across distant units, not only adjacent functions.
- Look for duplicated calculations, counters, validation, parsing, state, and
  representations.
- Check whether two successive owners perform different names for the same work,
  or whether one owner partially performs another owner’s job.
- Prefer eliminating work over wrapping duplicated work in another abstraction.

### 3. Design-improvement pass

For every awkward part, ask:

- Do we need this at all?
- Can the design eliminate the state, branch, format, or recovery path?
- Can one focused component centralize genuinely repeated logic?
- Should an overloaded component be decomposed by contract?
- Would a plain dictionary, tuple, or direct function be clearer than a type or
  subsystem used in one place?
- Is generality being purchased at the expense of correctness,
  maintainability, speed, or concision?
- Is this awkwardness evidence against the design, or merely pressure to corrupt
  the gate around it?

### 4. Documentation pass

- A blind reader must understand why every nontrivial class exists from its
  docstring.
- Document what a calculation tells the user, not merely which tensor operations
  it performs.
- Explain lifecycle boundaries, authority, intentional state, approximations,
  and surprising framework constraints where they occur.
- Preserve useful comments during rewrites. Concision never justifies making
  code unauditable.
- Keep gate conditions, accepted design, active-plan sequence, and future-gate
  obligations in their proper homes.

### 5. Fresh adversarial pass

Reread the modified unit from the beginning as if encountering it for the first
time. Do not ask “can I prove the whole system correct?” Ask:

> Did I screw up this unit?

Look especially for misleading names, missing explanations, accidental second
sources of truth, hot-path validation, hidden recomputation, pending-state
machinery, one-use abstractions, stale development terminology, behavior that
exists only to compensate for an earlier design mistake, design assumptions that
have leaked upward into acceptance criteria, and active-plan decisions that have
leaked forward into later milestones.

## Technical reduction method

When a unit becomes hard to reason about:

1. Summarize each class and top-level function—not every method—in up to three
   sentences. Describe what the code actually does from evidence, not what its
   abstraction was intended to be.
2. Add up to five supporting details only when needed.
3. Compare the summaries. Repeated work, overlapping ownership, and incompatible
   stages become candidate design defects.
4. Walk the code again. Anything substantial that did not fit its owner’s
   summary is a potential responsibility leak.
5. For each mismatch, decide whether the gate, design, plan, artifact, or
   component is wrong, or whether the component should be removed or redesigned.

This method requires concrete and abstract reasoning together: follow the real
classes and data flow, then judge whether their responsibilities form a coherent
system.

## Five-objective review

Balance all five independently. Do not sacrifice one silently to optimize
another.

### Effective

- Does the unit produce the information or behavior the project actually needs?
- Are important products accidentally disabled, deferred, or routed nowhere?

### Fast

- Is unnecessary work absent from the normal path?
- Are calculations reused at their natural feedstock?
- Are discovery, formatting, validation, synchronization, and file operations
  kept out of hot paths?

### Maintainable

- Does each responsibility have a clear owner?
- Can a blind reader audit the behavior from structure and documentation?
- Is intentional state small, local, and justified by a real lifecycle gap?

### Correct

- Is algebra owned by the component that defines it?
- Are lifecycle boundaries, authority, failure behavior, and sources of truth
  explicit?
- Does crash behavior roll back to authoritative state rather than repair
  speculative state?

### Concise

- Has unnecessary machinery been removed rather than renamed?
- Does every abstraction eliminate repetition or establish a necessary contract?
- Could ordinary language structures express the same idea more clearly?

## Verification and completion

- Compilation is only a syntax gate.
- Test contracts and failure ordering, not merely happy-path execution.
- Verify persistence, resume, and authority in the order they actually occur.
- Regenerate derived artifacts and check that regeneration is deterministic.
- Perform one final source-order adversarial read after all fixes.
- Report design deviations, deliberate approximations, remaining integration
  gates, and downstream work explicitly.
- Never say a wave, unit, plan, or milestone is complete when only its first
  runnable draft exists.
- Before milestone closure, rerun the gate review tests against the delivered
  solution and verify that no current implementation detail has become a hidden
  acceptance clause.
- Before carrying a discovered requirement forward, update the owning future gate
  through explicit review rather than extending the active plan across milestone
  boundaries.

## Communication and feedback

Work as a senior engineering partner. Make ordinary in-scope improvements
autonomously and report them. Surface major design unlocks before choosing them.
When challenged, investigate the design rather than defending the current
artifact.

Treat criticism as evidence, not automatically as a literal patch instruction.
Identify the underlying contract, responsibility, or reader-model problem;
correct the owning artifact; then rerun the independent review passes to ensure
the latest correction did not damage the rest of the system.

The objective is maximum quality under the five criteria, not preservation of
the first implementation or original plan.
