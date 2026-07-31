# Preliminary behavioral test contracts

Status: preliminary constraints for design and later executable acceptance tests.

This document identifies behaviors whose failure would establish that a Clan
Tuning implementation is wrong. It does not define the public API, internal
components, framework extension points, file layout, or milestone decomposition.
It is scratchwork until reviewed and promoted into an owning design or gate.

The contracts intentionally name observable state partitions rather than using
phrases such as "full state." Unless a contract says otherwise:

- **model state** means model parameters and persistent model buffers;
- **optimizer state** means the optimizer tensors and history associated with the
  model parameters, excluding the current member-local hyperparameter values;
- **member identity** means the stable identity of one population slot or live
  member;
- **member configuration** means the optimizer hyperparameter values assigned to
  that member for a round;
- **round result** means one member's fitness and the identity of the completed
  round that produced it; and
- **transition decision** means the selected parent and the next member
  configurations produced from one complete population of round results.

A later executable test may use any supported public facade. It should observe
these behaviors at the public or framework lifecycle boundaries rather than call
internal policy methods merely to make the assertion easy.

## Contract 1: one complete population produces one winner

### Test setup

Run a population in which every required member completes the same round and
reports a distinct, known fitness value under the configured metric direction.

### Required observations

- The selected parent is the member with the best reported fitness under the
  configured `min` or `max` rule.
- Every live member observes the same selected parent.
- The decision refers to the round that produced the supplied results.
- Exactly one parent is selected for that transition.

### A failing test proves

Selection used the wrong fitness rule, different members resolved different
parents, stale results entered the decision, or the implementation did not form a
single sole-parent transition.

## Contract 2: selection is based on comparable member-local fitness

### Test setup

At one common round boundary, evaluate every member on the same held-out examples
under equivalent evaluation settings. Construct the members so their local model
states produce distinguishable fitness values.

### Required observations

- Each reported fitness is computed from that member's own model state.
- Every member is evaluated at the same logical round boundary.
- Every member is evaluated against the same held-out workload and metric
  definition.
- Candidate fitness values remain distinct inputs to selection; they are not
  averaged or reduced into one population-wide score.

### A failing test proves

The winner comparison was not meaningful because candidates were evaluated under
different conditions, at different lifecycle positions, from the wrong model
state, or after candidate scores had been combined.

## Contract 3: all members train from one shared gradient

### Test setup

Run at least two live members with independently partitioned training batches and
member-local optimizer configurations. Choose a deterministic step for which the
unreduced local gradients differ.

### Required observations

- Before each member performs its optimizer update, corresponding trainable
  parameters have the same reduced gradient on every member.
- The reduced gradient includes the contribution required by every live member in
  the clan.
- Member-local optimizer state and configuration remain local; only the gradient
  is shared at this boundary.

### A failing test proves

The members are training independently rather than as one shared-gradient clan,
the distributed population is incomplete, or member-local optimizer state has
been incorrectly synchronized.

## Contract 4: member-local optimization can produce member divergence

### Test setup

Begin from equal model state and equal optimizer history. Supply the same reduced
gradient to members whose assigned optimizer configurations are deliberately
chosen to produce different updates.

### Required observations

- Members begin the tested update from equal model state.
- Members use equal reduced gradients for the tested update.
- Each member applies its own assigned optimizer configuration.
- The resulting model states differ in the way implied by those local optimizer
  configurations.

### A failing test proves

Member-local optimizer behavior was erased, the wrong configuration was applied,
model state was unintentionally synchronized after the optimizer step, or the
observed divergence came from unequal starting state or unequal gradients rather
than Clan Tuning.

## Contract 5: the selected model and optimizer history become the sole parent

### Test setup

Complete a round whose winner has model state and optimizer history distinguishable
from every losing member. Resolve the transition, but observe every receiving
member before any next-round training update.

### Required observations

- Every receiving member's model state equals the winner's accepted round-end
  model state.
- Every receiving member's optimizer state equals the winner's accepted round-end
  optimizer state.
- No losing member's model values or optimizer-history values survive in any
  receiver.
- All receivers identify the same source member for the inherited state.

### A failing test proves

The wrong member was copied, states were averaged or mixed, only part of the
continuation state was inherited, different receivers used different parents, or
a losing trajectory survived the transition.

This contract does **not** require copying member identity, member configuration,
controller internals, random streams, framework runtime objects, or other state
not explicitly named above.

## Contract 6: inheritance preserves receiving-member identity and next configuration

### Test setup

Resolve a transition that assigns distinguishable next-round configurations to
multiple population slots. Observe the receivers after winner-state inheritance
and configuration application, but before the next training update.

### Required observations

- Every receiver retains its own member identity.
- Every receiver uses the next-round configuration assigned to that member.
- Applying the receiving member's configuration does not recreate, discard, or
  replace the inherited optimizer history.
- The winning member may retain the unmodified winning configuration when the
  accepted controller policy assigns it; non-winning members use the distinct
  configurations assigned to them.

### A failing test proves

Copying the winner collapsed the population into one identity, configuration was
copied from the checkpoint instead of assigned for the next round, configuration
application reset inherited optimizer history, or assignments were delivered to
the wrong members.

## Contract 7: a partial population cannot transition

### Test setup

Cause one required member to fail, disappear, or omit its valid round result while
other members reach the transition boundary.

### Required observations

- No winner is selected from the partial population.
- No member begins the next round.
- No member loads or adopts a candidate parent state for the aborted transition.
- The active clan fails or is invalidated as a whole; it does not silently continue
  with a smaller population.
- The failure identifies enough member and round context to distinguish the broken
  population from an ordinary losing member.

### A failing test proves

The implementation can optimize over a different population than the configured
clan, perform a partial transition, or leave members on inconsistent generations.

## Contract 8: the transition supports continued multi-round training

### Test setup

Run enough work to complete a round, perform a winner transition, and complete at
least one additional round with the resulting population.

### Required observations

- Every member starts the later round from the state and configuration established
  by the preceding transition.
- Shared-gradient training and member-local optimization both resume after the
  transition.
- The later round produces one valid member-local fitness result per required
  member.
- The later population can produce another internally consistent transition
  decision.

### A failing test proves

The implementation can stage a one-off copy but cannot reform the clan, resume the
required distributed behavior, or repeat the actual tuning process.

## Contract 9: repeated execution from the same authoritative transition inputs is stable

### Test setup

Capture the authoritative inputs immediately before a transition decision. Execute
the transition twice from those same inputs under the same configured seed and
member identities.

### Required observations

- Both executions select the same parent.
- Both executions assign the same next configuration to each member.
- Both executions identify the same completed and next round.

### A failing test proves

The transition depends on hidden process history, inconsistent population order,
non-restored randomness, or another unrecorded source of authority.

This contract constrains observable transition output. It does not yet decide
which controller fields, random-generator states, or framework objects must be
persisted to reproduce that output.

## Promotion rule

Before implementation begins, the accepted system design should map each retained
contract to:

1. the supported public operation that triggers it;
2. the lifecycle boundaries at which its observations can be made;
3. the owner of every state partition named by the contract; and
4. one executable acceptance test or a documented reason the contract is proven
   by a narrower framework-contract test plus an end-to-end test.

Contracts may be revised or removed during design review. They must not be made
more specific merely to fit the first proposed implementation.
