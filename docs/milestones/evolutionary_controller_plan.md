# Evolutionary-controller milestone plan

Status: working rewrite for review

## Purpose

Produce the Milestone 2 project result: an independently invokable evolutionary controller that owns only the population decision required by Clan Tuning and fits the accepted synchronous Ray PBT decision seam.

The plan is governed by the roadmap, accepted project decisions, Milestone 2 gate, and standing framework-native review. It is an execution route, not a second acceptance contract.

## Products

Milestone 2 develops together:

- the public controller and transition-decision representation;
- focused policy, invalid-input, determinism, completion, and persistence tests;
- one narrow version-specific contract test for the selected PBT decision seam;
- controller design, API/configuration, transition-record, limitation, and failure documentation;
- an independently runnable controller example with inspectable population input and transition output;
- the Milestone 3 integration handoff.

Milestone 3 will compose these controller products with the real Lightning/DDP, data, checkpoint, trial, and resource lifecycle.

## Controller responsibility

The controller's main idea is:

> Given one complete population result, decide the sole parent, elite and target optimizer configurations, lineage, and whole-population continue/complete outcome.

It owns policy and only the state required to reproduce that policy. It emits a decision for framework-owned execution; it does not execute training or state transfer.

## Work method

Each work unit includes its implementation, focused tests, affected documentation, transition-record behavior, and example update. After each unit:

1. run the relevant policy and seam tests;
2. summarize the unit's actual main idea and supporting details;
3. check for duplicated Ray lifecycle or a second experiment schema;
4. update the controller docs and example at the level now externally meaningful;
5. apply the standing framework-native review;
6. reopen the accepted PBT-specialization decision if the seam cannot express the policy cleanly.

## Work unit 1 — qualify the PBT decision seam

### Purpose

Establish the exact Ray extension point through which ClanBasedTuning can replace the population decision without reproducing Tune orchestration.

### Work

Inspect the qualified Ray source and build the smallest real seam test that establishes:

- when the population decision is invoked;
- which member identities, metrics, configurations, and scheduler state are available;
- how one source, all targets, target configurations, and collective completion can be expressed;
- what policy state the scheduler seam persists;
- which upstream changes would break the contract.

Keep the test claim at the decision seam. The complete native trial and checkpoint lifecycle is exercised when Milestone 3 integrates the controller into a real workflow.

### Repair condition

If the seam cannot express the public controller contract without reproducing substantial Tune control flow, stop and reopen project decision P3 with the observed evidence.

### Exit products

- version-specific PBT decision-seam contract test;
- short seam/ownership design note;
- exact input/output constraints for the public controller.

## Work unit 2 — define the public population and transition contracts

### Purpose

Make the controller independently invokable and keep framework objects out of the policy model where they add no contract value.

### Work

Define the smallest public representation for:

- complete member population input;
- fitness direction and member identity;
- current optimizer configuration and lineage information;
- sole parent, elite, target configurations, continue/complete outcome, and transition record.

Use plain data structures where they express the contract clearly. Do not introduce a general experiment schema.

### Exit products

- reviewed public contract;
- serialization/round-trip tests for intentional controller state and records;
- API/reference draft and example skeleton.

## Work unit 3 — implement deterministic selection and complete-population validation

### Purpose

Produce one valid, explainable parent decision from one complete population.

### Work

Implement and test metric mode, ranking, tie behavior, missing/duplicate members, NaN/infinite fitness, population completeness, deterministic winner identity, complete target set, and transition explanation.

### Exit products

- focused selection/validation tests;
- visible winner and target reasoning in the transition record and example;
- updated policy documentation.

## Work unit 4 — implement elite and optimizer-only mutation policy

### Purpose

Generate the next optimizer population without changing the shared-gradient workload.

### Work

Define the smallest mutation contract that accepts legal optimizer values, retains exactly one elite, produces legal target configurations, and rejects model/data/batch/augmentation or other gradient-defining mutations. Use native Ray mutation facilities only where they match this contract.

### Exit products

- mutation and invalid-surface tests;
- configuration reference and example output;
- evidence that no second experiment language was introduced.

## Work unit 5 — implement collective outcome and controller persistence

### Purpose

Ensure the policy acts on a complete population and survives only through the state required by its selected scheduler seam.

### Work

Implement and test whole-population continue/planned-completion decisions, invalid-population refusal, deterministic policy state, and scheduler state serialization only where the seam requires it.

Process termination and trial-state execution remain on the native framework path that Milestone 3 will compose around this policy.

### Exit products

- completion/failure-ordering tests;
- persistence test for intentional controller state;
- failure/limitation documentation and transition records.

## Work unit 6 — complete the public controller products

### Purpose

Make the subsystem independently usable, reviewable, and ready for manual integration.

### Work

- complete the controller design and public API/configuration/reference documentation;
- complete focused and PBT decision-seam test suites;
- build the standalone controller example with explicit population input and inspectable transition output;
- explain how to run the example and interpret the decision;
- produce the Milestone 3 handoff containing the public inputs, outputs, state, seam, and integration responsibilities.

### Exit condition

Implementation, tests, documentation, example, and handoff agree on one controller contract and satisfy the Milestone 2 gate.