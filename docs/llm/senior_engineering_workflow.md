# Senior engineering workflow

This guide defines the standing process for serious ClanBasedTuning engineering
work. It is not a milestone checklist and does not replace the governing roadmap,
decisions, gates, or accepted design.

## Core imperative

Continuously evaluate and improve the design while implementing it. Never narrow
the job to “make the requested patches,” and never treat “runs and compiles” as
equivalent to “finished.” Every implementation and review pass must consider
whether the contract, ownership, or design itself is wrong.

Minor design corrections may be made and reported afterward. A change that
unlocks new behavior, changes scientific meaning, alters authority or recovery,
or materially expands scope must be discussed before implementation.

## Before coding

1. Read the authoritative gate, accepted design or plan, current artifact,
   relevant comments, and nearby consumers. Do not reconstruct intent from names
   alone.
2. State the success criteria and current implementation boundary. Distinguish
   “this unit is complete” from “the whole milestone is complete.”
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

### 4. Documentation pass

Documentation is a forcing function for design quality, not a coverage target.
The purpose is to preserve knowledge that a future maintainer cannot cheaply
recover from the syntax alone.

- A blind reader must understand why every nontrivial class exists from its
  docstring.
- Every retained function or method must earn its abstraction. It should either
  establish a real contract/invariant, centralize genuinely repeated behavior,
  isolate an external-effect or compatibility seam, or be required by a
  framework/public interface.
- If the best docstring for a private helper merely paraphrases its name,
  signature, or obvious implementation, treat that as a refactoring signal:
  first ask whether the helper should be inlined, merged into its owner, or
  removed rather than manufacturing a longer description.
- Small framework-required methods are not automatically unnecessary. Their
  documentation should explain the framework assumption being adapted or the
  failure that the override prevents, not state that a getter “returns” its
  field.
- Useful function/class documentation records non-obvious ownership, lifecycle,
  ordering, failure semantics, invariants, deliberate alternatives, or reasons a
  boundary exists. Do not fill `Args`, `Returns`, or comments with information
  already obvious from names and types unless the parameter carries a hidden
  contract.
- Document what a calculation tells the user, not merely which operations it
  performs.
- Explain lifecycle boundaries, authority, intentional state, data structures,
  algorithms, approximations, and surprising framework constraints where they
  occur.
- Preserve useful comments during rewrites. Concision never justifies making code
  unauditable, but verbosity that adds no recoverability is not maintainability.

A useful adversarial question is:

> If this comment or docstring disappeared, what maintenance knowledge would
> become materially harder to recover?

If the answer is “none,” either improve the documentation with real design
knowledge or reconsider the abstraction it is attached to.

### 5. Fresh adversarial pass

Reread the modified unit from the beginning as if encountering it for the first
time. Do not ask “can I prove the whole system correct?” Ask:

> Did I screw up this unit?

Look especially for misleading names, missing explanations, accidental second
sources of truth, hot-path validation, hidden recomputation, pending-state
machinery, one-use abstractions, stale development terminology, and behavior
that exists only to compensate for an earlier design mistake.

## Technical reduction method

When a unit becomes hard to reason about:

1. Summarize each class and top-level function—not every method—in up to three
   sentences. Describe what the code actually does from evidence, not what its
   abstraction was intended to be.
2. Add up to five supporting details only when needed.
3. Compare the summaries. Repeated work, overlapping ownership, and incompatible
   stages become candidate design defects.
4. Walk the code again. Anything substantial that did not fit its owner’s summary
   is a potential responsibility leak.
5. For each mismatch, decide whether the contract is wrong, the artifact is wrong,
   or the component should be removed or redesigned.

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

## Review-unit rule

A pull request is a reviewable engineering unit, not a progress dump or a request
for design consultation.

- It performs one coherent small-to-medium task.
- It leaves the repository in a stable, mergeable intermediate state.
- Its code, tests, and documentation agree on the contract introduced by that
  unit.
- It does not bundle unrelated authority repair, design selection, implementation,
  integration, and cleanup merely because they belong to the same milestone.
- A proposal or scratch note is not a sufficient PR unless the repository needs
  that durable artifact independently of the conversation.
- Large work is split at real stable boundaries, such as accepted design,
  implementation, framework integration, and usability.

Before opening a PR, perform a review-cost pass: identify what a human must
understand, whether the diff answers one review question, and whether any subset
should be accepted first.

## Verification and completion

- Compilation is only a syntax gate.
- Test contracts and failure ordering, not merely happy-path execution.
- Verify persistence, resume, and authority in the order they actually occur.
- Regenerate derived artifacts and check that regeneration is deterministic.
- Perform one final source-order adversarial read after all fixes.
- Report design deviations, deliberate approximations, temporary lint or test
  exclusions, remaining integration gates, and downstream work explicitly.
- Never say a wave, unit, plan, or milestone is complete when only its first
  runnable draft exists.

## Communication and feedback

Work as a senior engineering partner. Make ordinary in-scope improvements
autonomously and report them. Surface major design unlocks before choosing them.
When challenged, investigate the design rather than defending the current
artifact.

Treat criticism as evidence, not automatically as a literal patch instruction.
Identify the underlying contract, responsibility, or reader-model problem;
correct the owning artifact; then rerun the independent review passes to ensure
the latest correction did not damage the rest of the system.

The objective is maximum quality under the five criteria, not preservation of the
first implementation or original plan.
