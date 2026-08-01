# Engineering workflow

Use this workflow for substantial design, implementation, debugging, refactoring, integration, and review.

It does not replace the project roadmap, decisions, architecture, contracts, current source, or human review.

## Core rule

Continuously evaluate the design while implementing it. A unit that runs is still a draft until its contract, ownership, failure behavior, documentation, and evidence survive review.

Minor in-scope corrections may be made and reported. Changes to Clan Tuning meaning, state authority, recovery, public support, or milestone scope require explicit review before implementation.

## Before changing code

1. Identify the requested result and a coherent PR-sized review unit.
2. Read [`../README.md`](../README.md), the relevant authority and contracts, current source, tests, consumers, and framework evidence.
3. State what the unit owns, what it does not own, and what observable result will establish completion.
4. Search for duplicated implementations, state, validation, representations, and remote consumers before introducing an abstraction.
5. Redesign overloaded or unnecessary machinery before extending it.

## Implementation passes

### Contract

- Does every component have one coherent purpose?
- Does data leave it in the form promised by its contract?
- Has orchestration absorbed policy, calculation, storage, or framework behavior owned elsewhere?
- Are lifecycle, authority, and failure ordering explicit?

### Boundaries and duplication

- Search beyond adjacent files for repeated calculations, validation, state, and representations.
- Prefer eliminating duplicated work over wrapping it.
- Avoid second sources of truth and mirrored configuration without a real lifecycle need.
- Use ordinary data structures unless a type establishes a necessary contract.

### Design reduction

For awkward machinery ask:

- Is it needed?
- Can the design eliminate the state, branch, format, or recovery path?
- Should responsibility move to its natural owner?
- Is generality being purchased at the expense of correctness, maintainability, speed, auditability, or concision?

When a system is hard to reason about, summarize each class and top-level function in up to three sentences. Anything substantial that does not fit its owner's summary is a responsibility leak or a sign that the contract is wrong.

### Documentation

- Preserve useful comments and design reasons.
- Explain why nontrivial components exist, what they own, and why surprising framework constraints matter.
- Keep documentation synchronized with accepted design and actual source.
- Do not create a competing summary merely because the current file is convenient to edit.

### Fresh adversarial review

Reread the changed unit in source order as a new reviewer. Look for misleading names, hidden recomputation, accidental authority, one-use abstractions, stale terminology, hot-path ceremony, and behavior that only compensates for an earlier design error.

Ask: **Did this unit introduce the simplest correct ownership model, or merely make the current shape pass?**

## Five objectives

Review the unit independently for:

- **Effective:** it produces the required behavior and information.
- **Correct:** algebra, authority, lifecycle, failure, and recovery are owned and ordered properly.
- **Maintainable:** responsibilities and intentional state are clear and auditable.
- **Fast:** unnecessary synchronization, conversion, validation, discovery, and I/O are absent from normal paths.
- **Concise:** every abstraction eliminates repetition or establishes a necessary contract.

Do not silently trade one objective for another.

## Framework-native review

Whenever a unit changes a PyTorch, Lightning, or Ray boundary, apply these checks in order:

1. **Preserve Clan meaning.** The complete live population contributes to shared-gradient training, variation remains optimizer-side during a round, fitness is comparable, and one selected parent supplies the next continuation.
2. **Use the native owner.** Ordinary scheduling, training, validation, distribution, checkpoint, optimizer, data, resource, and lifecycle behavior stays with the framework that already owns it.
3. **Demonstrate the gap.** Custom behavior names the required Clan behavior, the native mismatch, the smallest seam, and evidence that ordinary composition is insufficient.
4. **Keep one authority.** The custom seam adds only the missing Clan behavior and does not create mirrored policy or state.
5. **Match support to evidence.** Version-sensitive, distributed, persistence, recovery, performance, and failure claims require direct source evidence or executable qualification.

The result is **pass**, **fail**, or **insufficient evidence**. Narrow unsupported claims rather than treating plausible behavior as qualified.

## Tests and evidence

- Compilation is only a syntax gate.
- Test contracts and failure ordering, not only happy-path execution.
- Verify persistence, resume, and authority in the order they occur.
- Fake collaborators establish local behavior, not distributed integration support.
- Hardware, backend, and topology claims require direct qualification on that path.
- Regenerate derived artifacts and confirm deterministic regeneration where applicable.

## Pull requests

A PR is a reviewable engineering unit, not a progress dump or design question.

It must:

- perform one coherent small-to-medium task;
- leave a stable, mergeable repository state;
- keep its title, body, diff, tests, and documentation in sync;
- distinguish implementation from proposed design and evidence from support claims; and
- separate architecture, implementation, integration, and unrelated cleanup when each can stand alone.

Before opening a PR, identify what the reviewer must understand and whether a smaller stable subset should be accepted first.

Do not modify CI/workflow files or merge PRs without explicit authorization.

## Completion and communication

Report what was implemented, what was only designed or qualified, deliberate approximations, temporary exclusions, remaining integration gates, and downstream work.

Do not call a unit, plan, or milestone complete when only its first runnable form exists.

When feedback identifies a problem, locate the underlying contract, responsibility, or evidence defect. Correct the owning artifact, then rerun all affected review passes instead of optimizing only for the latest complaint.
