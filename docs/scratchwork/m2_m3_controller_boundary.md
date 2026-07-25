# Proposed M2/M3 controller responsibility boundary

Status: preliminary proposal for human review; not project authority

## Decision under review

Milestone 2 should deliver the independently invokable Clan evolutionary policy.
Milestone 3 should choose and qualify how Ray Tune supplies that policy with a
completed population and executes its decision.

This separates two questions that the current documentation combines:

1. What population-policy capability does ClanBasedTuning own?
2. How does the Ray-backed workflow invoke that capability through native framework
   lifecycle?

## Proposed allocation

### Milestone 2

Milestone 2 defines and proves a framework-independent controller boundary. The
controller consumes ordinary data representing one complete population result and
produces the selected parent plus the next optimizer-hyperparameter configurations.

Milestone 2 may test the plain data shape expected after framework extraction, but it
does not import Ray trial objects, subclass a Tune scheduler, select a private Ray
hook, transfer checkpoints, or execute trial lifecycle.

### Milestone 3

Milestone 3 chooses the narrowest Ray-native invocation path from direct framework
evidence. It may compare a scheduler specialization with a thin adapter around the
accepted controller, then proves the selected path through framework-contract and
end-to-end tests.

Ray continues to own trial execution, checkpoint and configuration assignment,
pause and resume, resources, and scheduler lifecycle. Lightning continues to own
training cadence, optimizer construction, checkpoint contents, and restoration.

## Why this allocation is narrower

The independent population policy can be designed, tested, documented, and
understood without importing an execution framework. Making the Ray invocation form
part of Milestone 2 forces integration constraints into the controller before its own
contract is settled.

Moving the invocation decision to Milestone 3 does not defer controller capability.
It leaves Milestone 2 with the complete policy product and assigns translation and
execution to the milestone that already owns the real Ray/Lightning/PyTorch workflow.

## Deliberate non-decisions

This proposal does not decide:

- whether the controller is stateful or receives explicit randomness;
- the public API, class layout, or concrete population representation;
- the mutation distribution, boundary behavior, or tie policy;
- how optimizer hyperparameters are declared by users;
- which Ray extension point Milestone 3 will select.

Those questions require their own design and review.

## Authority changes after acceptance

A separate, narrowly scoped PR would apply this decision to only the artifacts that
own it:

- project decision P3;
- the Milestone 2 gate;
- the Milestone 3 gate;
- the active Milestone 2 execution plan; and
- the framework-alignment explanation of the M2/M3 split.

It would not rewrite the root README, roadmap, project status, review history, LLM
operating context, controller implementation, tests, or examples.

## Review question

Should Milestone 2 end at the independent population-policy contract, with selection
and qualification of the Ray invocation path moved to Milestone 3?
