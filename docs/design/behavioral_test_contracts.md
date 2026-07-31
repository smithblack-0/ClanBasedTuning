# Behavioral test contracts

Status: proposed design contract under human review  
Date: 2026-07-31

## Purpose

These contracts identify observable outcomes whose failure would prove that a
Clan Tuning implementation is behaviorally wrong. They constrain the design and
later executable acceptance tests without choosing a public facade, scheduler
class, callback layout, transport, or file structure.

The contracts are intentionally incomplete as a feature inventory. They cover the
mechanism-defining conditions that must remain true through any acceptable
implementation. Additional tests may be required for a selected design, framework
version, support boundary, or public API.

## State vocabulary

The contracts avoid phrases such as "full state" because different state must
follow different authorities during a generation transition.

- **Model state** means model parameters and persistent model buffers.
- **Optimizer history** means optimizer tensors, counters, moments, momentum, and
  other accumulated state associated with model parameters. It excludes the
  controlled hyperparameter values assigned to a member for the next round.
- **Training-progress state** means the framework-owned continuation state needed
  to resume the same training point, including supported loop counters, global
  step, epoch, precision-scaler state, and supported scheduler state.
- **Continuation state** means model state, optimizer history, and
  training-progress state together.
- **Member identity** means the stable identity of one population slot or live
  member.
- **Member configuration** means the controlled optimizer hyperparameter values
  assigned to that member for one round.
- **Controller state** means the target member's current round, local random
  stream, current controlled configuration, and other state owned by the accepted
  evolutionary controller.
- **Framework runtime state** means live process, actor, process-group, device,
  launcher, and similar objects that exist only to execute a run.
- **Round result** means one member's fitness, member identity, round identity,
  and controlled configuration at the completed boundary.
- **Transition decision** means the sole selected parent and the next member
  configuration produced for every member from one complete population of round
  results.

A later executable test should observe these partitions at public or native
framework lifecycle boundaries. It should not call an internal method merely
because doing so makes the assertion easier.

## Contract 1: every round begins from one common continuation state

### Test setup

Observe every member immediately before its first training update in a round.
Use continuation-state values that can be distinguished from stale or losing
state. Assign at least two members different controlled optimizer
configurations.

### Required observations

- Every member has equal model state.
- Every member has equal optimizer history.
- Every member has equal training-progress state.
- Each member retains its own member identity.
- Each member has the configuration assigned to that member for the observed
  round.
- Framework runtime objects may differ and are not part of the equality claim.

### A failing test proves

The clan did not begin from one common trajectory, a member retained stale state,
member identity was overwritten during cloning, or controlled configuration was
incorrectly included in the common continuation state.

## Contract 2: one complete population produces one winner

### Test setup

Complete one round with exactly one valid result for every required member and
with distinct known fitness values under the configured metric direction.

### Required observations

- The selected parent is the member with the best reported fitness under the
  configured `min` or `max` rule.
- Every member and the external transition executor identify the same parent.
- The decision refers to the round that produced the supplied results.
- Exactly one parent is selected.

### A failing test proves

Selection used the wrong fitness rule, different participants resolved different
parents, stale results entered the decision, or the transition did not have one
sole parent.

## Contract 3: selection compares equivalent member-local fitness

### Test setup

At one common round boundary, evaluate every member on the same held-out examples
under equivalent evaluation settings. Construct members whose local model states
produce distinguishable fitness values.

### Required observations

- Each fitness value is computed from that member's own model state.
- Every member is evaluated at the same logical round boundary.
- Every member sees the same held-out workload, ordering rules, transforms, and
  metric definition within the supported test configuration.
- Candidate fitness values remain separate inputs to population selection; they
  are not averaged or reduced into one population-wide score.

### A failing test proves

The comparison was not meaningful because candidates were evaluated at different
boundaries, against different work, from the wrong model state, or after their
scores had been combined.

## Contract 4: every optimizer update uses one clan-wide reduced gradient

### Test setup

Run at least two live members on independently partitioned training batches.
Choose a deterministic update for which the unreduced local gradients differ.

### Required observations

- Immediately before the optimizer update, corresponding trainable parameters
  have equal reduced gradients on every member.
- The reduced gradient contains the required contribution from every live member
  in the clan.
- Optimizer history and member configuration remain local; only the gradient is
  shared at this boundary.
- No required member is queued, omitted, or time-multiplexed outside the tested
  collective.

### A failing test proves

Members trained independently, the active population was incomplete, the wrong
collective was used, or optimizer-side state was synchronized together with the
gradient.

## Contract 5: member-local optimization produces controlled divergence

### Test setup

Begin one update from equal model state and equal optimizer history. Supply the
same reduced gradient to members with configurations deliberately chosen to
produce different updates.

### Required observations

- Members begin the update from equal model state and optimizer history.
- Members use equal reduced gradients.
- Each member applies its own assigned configuration through its own optimizer
  history.
- Resulting model states differ in the way implied by the local optimizer
  behavior.
- No post-update parameter or persistent-buffer synchronization erases intended
  member divergence.

### A failing test proves

Member-local optimizer behavior was erased, a configuration was delivered to the
wrong member, model state was resynchronized after the update, or apparent
divergence came from unequal inputs rather than Clan Tuning.

## Contract 6: the winner's continuation state is the sole inherited parent

### Test setup

Complete a round whose winner has model state, optimizer history, and
training-progress state distinguishable from every losing member. Observe every
receiver after inheritance and before the next training update.

### Required observations

- Every receiver's model state equals the winner's accepted round-end model
  state.
- Every receiver's optimizer history equals the winner's accepted round-end
  optimizer history.
- Every receiver's training-progress state equals the winner's accepted
  round-end training-progress state.
- Every receiver identifies the same source member for inherited continuation
  state.
- No distinguishable continuation-state value from a losing member survives in
  any receiver.

### A failing test proves

The wrong member was copied, continuation states were averaged or mixed, only a
partial continuation was inherited, different receivers used different parents,
or a losing trajectory survived.

This contract does not require copying member identity, member configuration,
controller state, or framework runtime state.

## Contract 7: inheritance preserves target-local identity and control state

### Test setup

Resolve a transition that produces distinguishable next configurations and
controller states for multiple members. Observe receivers after winner
continuation-state restoration and configuration application but before the next
training update. Continue far enough to make target-local controller randomness
observable in a later decision.

### Required observations

- Every receiver retains its own member identity.
- Every receiver retains the controller state produced for that target member,
  rather than receiving the winner's controller state.
- Every receiver uses the next configuration assigned specifically to it.
- Applying the receiving configuration does not recreate, discard, or replace
  inherited optimizer history.
- Reapplying controlled values changes only their declared optimizer fields.
- Later target-local mutations follow the receiving member's continued random
  stream rather than the winner's stream.

### A failing test proves

Cloning collapsed the population into one identity, winner-local control state
was copied to every target, configuration was taken from the checkpoint instead
of the decision, or configuration application destroyed inherited optimizer
history.

## Contract 8: a partial population cannot produce or execute a transition

### Test setup

Cause one required member to fail, disappear, duplicate its result, report the
wrong round, or omit a valid result while other members reach the boundary.

### Required observations

- No valid transition decision is produced from the partial or corrupt
  population.
- No candidate checkpoint is assigned as the next parent.
- No member begins the next round.
- The active clan is failed or invalidated as a whole; it does not silently
  continue with fewer members.
- Blocked members are released by failure rather than waiting indefinitely.
- The surfaced failure identifies the affected member and round well enough to
  distinguish the broken population from an ordinary losing member.

### A failing test proves

The implementation can optimize over a different population than configured,
perform a partial transition, leave members on inconsistent generations, or hang
without exposing collective invalidation.

## Contract 9: the complete lifecycle repeats for multiple rounds

### Test setup

Complete a round, execute the sole-parent transition, and complete at least one
additional round with the resulting population.

### Required observations

- The later round begins from the continuation state, identities, controller
  states, and configurations established by the preceding transition.
- The distributed group is valid before later-round training begins.
- Shared-gradient training and member-local optimization both resume.
- The later round produces one comparable member-local fitness result per
  required member.
- The later complete population can produce and execute another internally
  consistent transition.

### A failing test proves

The implementation can stage a one-off copy but cannot reform the clan, resume
its defining distributed behavior, or repeat the actual tuning process.

## Contract 10: transition output is stable from the same authoritative inputs

### Test setup

Capture the complete population results and every target controller state
immediately before a transition decision. Execute the decision twice from those
same inputs under the same configured experiment seed and member identities.

### Required observations

- Both executions select the same parent.
- Both executions assign the same next configuration to each member.
- Both executions produce equivalent next controller state for each member.
- Both executions identify the same completed and next rounds.

### A failing test proves

The transition depends on population iteration order, hidden process history,
non-restored randomness, or another unrecorded source of authority.

## Design and implementation traceability

Before implementation begins, the accepted architecture must map each retained
contract to:

1. the lifecycle operation that triggers it;
2. the boundaries where each observation can be made;
3. the owner of every named state partition;
4. the framework assumptions that require direct contract tests; and
5. an executable acceptance test or a documented combination of focused and
   end-to-end evidence that proves the behavior.

A contract may be revised during design review. It must not be made more specific
merely to accommodate the first proposed implementation.
