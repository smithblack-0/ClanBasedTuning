# Milestone 2 gates — evolutionary subsystem

Status: working rewrite for review

## Milestone result

ClanBasedTuning has an independently invokable, tested, documented, and inspectable evolutionary controller that expresses the population-decision side of Clan Tuning through the accepted synchronous Ray PBT decision seam.

## Capability and responsibility gates

### M2.1 The public controller contract is complete

The controller consumes one complete population result containing the member identity, fitness, current optimizer configuration, and lineage information required by the policy. It produces one inspectable transition decision containing:

- the sole winning member whose model parameters, optimizer state, and optimizer configuration are declared as the only next-generation source;
- the elite optimizer configuration;
- the complete target-member set;
- the legal optimizer-only configuration assigned to each next-generation member;
- the collective continue or planned-completion outcome;
- the policy and lineage information required to explain the decision.

### M2.2 Population decisions are deterministic and valid

- Metric direction and tie behavior are explicit.
- Missing, duplicate, NaN, infinite, or incomplete population input fails clearly.
- Exactly one winner and one complete target set are produced.
- Repeated execution from the same controller state and input produces the same result.

### M2.3 Mutation remains optimizer-only

- The accepted mutation surface identifies optimizer values without becoming a second experiment configuration language.
- Model, data, batch, augmentation, and other gradient-defining mutation declarations are rejected.
- Exactly one elite configuration remains unmutated and every other resulting configuration is legal under the declared mutation contract.

### M2.4 The PBT specialization is narrow

A version-specific upstream contract test proves that the selected Ray PBT extension point:

- exposes the complete population information the controller requires;
- permits the controller's winner, target, configuration, and collective-outcome policy to be expressed;
- preserves only controller/scheduler policy state that the seam genuinely requires;
- leaves Tune trial orchestration and state execution on the native PBT path established by the accepted project decisions.

If this seam cannot express the controller contract without substantial Tune control-flow duplication, the accepted specialization decision is reopened before an alternative controller is designed.

### M2.5 Controller failure and completion remain population-wide

The controller does not emit a partial evolutionary decision for a missing or invalid population. Planned completion is a decision about the complete population, not independent per-member stopping.

## Test gates

### M2.6 Focused tests prove the policy contract

The public controller suite covers metric modes, ties, invalid fitness, incomplete and duplicate populations, sole-parent selection, elite behavior, optimizer-only mutation, determinism, collective completion, transition records, and controller serialization where required by the selected seam.

### M2.7 The framework-contract test proves only the decision seam

The Ray-specific test invokes the real selected extension point and verifies that the public controller receives the expected population input and returns or applies the intended decision. Its claim is decision-seam compatibility; the complete training and state-transition lifecycle becomes enforceable in Milestone 3.

### M2.8 The controller remains independently invokable

The same public controller contract can be exercised directly from population results and optimizer configurations. Framework adapters do not become the only route to policy testing or use.

## Documentation gates

### M2.9 Controller documentation enables independent implementation and review

The milestone delivers:

- a controller design explaining its main idea, inputs, outputs, state, and ownership boundary;
- public API and configuration reference for fitness direction, tie policy, elite handling, mutation, completion, and transition records;
- failure and limitation documentation, including the exact Ray seam and evidence that would reopen it;
- an explanation of the relationship between a transition decision and the framework-owned execution that Milestone 3 will integrate.

A reader must not infer the controller policy from Ray internals or from a later integration example.

## Example gates

### M2.10 An inspectable controller example demonstrates the evolutionary decision

A small reproducible example uses the public controller with explicit population results and optimizer configurations. It makes the input population, selected winner, elite, target set, mutations, lineage, and collective outcome visible and explains how to read them.

Synthetic population results are appropriate because this milestone demonstrates the decision subsystem. The complete training and state-transition example is introduced by Milestone 3.

## Evidence, review, and handoff gates

### M2.11 The controller products agree

Implementation, focused tests, Ray decision-seam test, documentation, transition records, and example describe one public controller contract. Human review applies the standing framework-native review and records any reopened decision.

### M2.12 Milestone 3 receives the complete controller handoff

The handoff states:

- the population result fields and completeness conditions the controller consumes;
- the transition decision and records it produces;
- the controller state that must persist;
- the exact Ray decision seam used;
- the point at which Milestone 3 connects the decision to native training, evaluation, checkpoint, state-transition, data, resource, and distributed behavior.

## Closure evidence

Milestone 2 closes with links to the accepted controller design and API, focused test results, Ray decision-seam contract result, controller example and output, transition-record reference, human review, and Milestone 3 handoff.