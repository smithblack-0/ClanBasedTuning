# Behavioral test contracts

Status: Milestone 3 behavioral acceptance contract  
Date: 2026-07-31

## Purpose

These contracts state the training behavior that ClanBasedTuning must produce. They
deliberately treat CBT as a black box around an ordinary distributed training job. A
test may provide fitness to CBT and inspect the resulting model, optimizer, training
progress, trial configurations, controller provenance, checkpoint artifacts, scheduler
recovery, and later training behavior.

Focused framework and unit tests protect the mechanisms used to deliver these outcomes;
they are not substitutes for observing the outcomes themselves.

## Observable training state

The contracts use state that an ordinary Tune and Lightning system can expose:

- **model state:** model parameters and persistent model buffers;
- **optimizer history:** accumulated optimizer tensors, counters, moments, momentum,
  and equivalent state, excluding newly assigned controlled values;
- **genome:** the controlled subset of the current Tune trial configuration assigned by
  the CBT scheduler;
- **controller genome snapshot:** the immutable copy of that current genome held only
  for winner provenance;
- **training-progress state:** framework continuation state such as global step, epoch
  or loop progress, precision state, and supported scheduler state;
- **fitness:** the result supplied to CBT for comparing one completed member with the
  others;
- **checkpoint payload:** the selected model, optimizer history, and training-progress
  continuation;
- **checkpoint producer metadata:** schema version, stable member ID, and the exact
  genome that produced the selected payload; and
- **scheduler transition state:** child genomes, mutation random state, lineage,
  checkpoint assignment, and recovery state for the next generation.

## Contract 1: every round begins from one common continuation

### Setup

Arrange a preceding round whose candidate states are distinguishable. Report results to
CBT so one candidate is unambiguously preferred. Observe every member at the beginning
of the next round, after restoration and before its first training update.

### Required behavior

- Every member has the preferred candidate's model state.
- Every member has the preferred candidate's optimizer history.
- Every member has the preferred candidate's training-progress state.
- No distinguishable model, optimizer-history, or progress value from a losing
  candidate survives.
- Genomes may differ because the scheduler assigns one target genome per trial after the
  common continuation is restored.

### Failure establishes

The next population did not descend solely from the preferred training trajectory, or
next-round variation was incorrectly mixed into the inherited continuation.

## Contract 2: child genomes are applied after inheritance

### Setup

Choose a preferred candidate whose checkpoint contains controlled optimizer values
distinguishable from the child genomes CBT will assign in the next round. Observe the
restored state before and after the current target `Trial.config` is applied, but before
a training update.

### Required behavior

- Model state and optimizer history first restore exactly from the preferred candidate.
- CBT then applies the intended child genome for each target member.
- Applying that genome changes only declared optimizer fields.
- Applying it does not recreate the optimizer, clear its history, change model
  parameters, or advance training progress.
- The shared checkpoint payload is not already mutated for one receiver's child role.

### Failure establishes

Mutation occurred before inheritance, one receiver's child genome was baked into the
common parent, or optimizer-history inheritance was destroyed while applying new
values.

## Contract 3: the controller snapshots the genome actually applied

### Setup

Construct one worker from a mutable genome mapping, create its controller, then mutate
the caller's original mapping before training or checkpoint annotation. Apply the
original assigned values to the optimizer.

### Required behavior

- The controller retains an independent snapshot of the assigned genome.
- Later mutation of the caller's mapping does not alter that snapshot.
- The snapshot equals the controlled values applied to the optimizer for the round.
- The controller does not itself apply or mutate the genome.

### Failure establishes

Checkpoint provenance can drift from the values that actually produced the worker's
result, or the controller has become a second live genome authority.

## Contract 4: Lightning DDP supplies one shared gradient

### Setup

Run at least two members on different training examples. Choose a deterministic update
for which their unreduced local gradients are distinguishable and the expected reduced
gradient is known.

### Required behavior

- Immediately before the optimizer update, corresponding trainable parameters in every
  member have the same reduced gradient.
- That gradient contains the required contribution from every active member.
- No required member is queued or omitted from the tested collective.
- Optimizer history and genomes remain local; only the gradient is shared at this
  boundary.

### Failure establishes

The members trained independently, the active population was incomplete, or
optimizer-side state was synchronized together with the gradient.

## Contract 5: local optimizer behavior produces the members

### Setup

Begin a deterministic update from equal model state and equal optimizer history. Use
the same reduced gradient while assigning genomes known to produce different updates.

### Required behavior

- Every member begins from equal model state and optimizer history.
- Every member receives the same reduced gradient.
- Each optimizer uses the controlled values assigned through that member's genome.
- The resulting model states differ as predicted by those optimizer updates.
- Later Lightning DDP activity does not overwrite the intended parameter or
  persistent-buffer divergence.

### Failure establishes

The genome was erased, assigned incorrectly, or confused with divergence caused by
different starting state or different gradients.

## Contract 6: fitness compares the actual local members

### Setup

Construct members whose local model states produce distinguishable evaluation results.
Evaluate them at one common round boundary on the same held-out workload under
equivalent conditions.

### Required behavior

- Each fitness value is computed from the model state of the member reporting it.
- Every member is evaluated at the same logical training boundary.
- The held-out examples, transforms, ordering rules, and metric definition are
  equivalent within the supported configuration.
- Candidate fitness values remain distinct when CBT compares them; they are not
  averaged into one population-wide result.

### Failure establishes

CBT compared unlike workloads, stale or foreign model state, different training
positions, or a fitness signal erased by distributed reduction.

## Contract 7: the preferred member is the one continued

### Setup

Complete a generation with distinguishable model state, optimizer history, training
progress, and active genome for each member. Report results so one member is
unambiguously preferred.

### Required behavior

- Exactly one continuation checkpoint is retained for the transition.
- Its payload matches the preferred member's model state, optimizer history, and
  training progress at the evaluated boundary.
- Before reporting, the selected controller writes producer metadata containing only
  schema version, that member's stable ID, and its copied current genome.
- The metadata member ID and genome match the scheduler-selected winner and the
  controlled subset of that winner's active `Trial.config`.
- The next generation restores that checkpoint into every member.
- No losing continuation is loaded, averaged, or mixed into any receiver.

### Failure establishes

CBT selected or persisted the wrong training trajectory, associated the artifact with
the wrong genome, retained multiple competing parents, or failed to make the reported
preference control the next generation.

## Contract 8: incomplete producer metadata is never published

### Setup

Cause the selected worker's checkpoint metadata update to fail after Lightning has
constructed the payload but before `tune.report()`.

### Required behavior

- The selected worker does not report that checkpoint.
- The scheduler does not accept an unannotated checkpoint as the next parent.
- No next-generation trial begins.
- The failure surfaces at the current generation boundary.

### Failure establishes

Tune can retain a training continuation whose producer genome cannot be verified, or a
scheduler crash can expose a half-complete artifact as valid.

## Contract 9: a partial population cannot advance

### Setup

Cause one required member to fail or omit valid fitness while the remaining members
reach the generation boundary.

### Required behavior

- No continuation checkpoint is accepted as the next parent.
- No member begins another generation.
- The active Clan fails or is invalidated as a whole rather than silently continuing
  with fewer participants.
- Waiting work is released by a surfaced failure rather than hanging indefinitely.
- The failure provides enough context to identify the broken population boundary.

### Failure establishes

The implementation can optimize over a population different from the configured Clan,
enter a mixed generation, or deadlock without reporting collective failure.

## Contract 10: the scheduler transition is all-or-nothing to workers

### Setup

Interrupt the scheduler after it has verified the winner but before all child genomes,
recovery state, and checkpoint assignments have been committed.

### Required behavior

- No target begins the next generation from a partial assignment.
- Recovery restores the last completed scheduler generation or fails the experiment.
- Mutation random state and lineage do not advance independently of the accepted child
  assignments.
- Every released target has both its intended child genome and the same selected
  checkpoint.

### Failure establishes

The scheduler can create mixed generations, duplicate or skip mutation transitions, or
recover from hidden state inconsistent with the trials it releases.

## Contract 11: the lifecycle repeats

### Setup

Complete a generation, transition through the preferred checkpoint and scheduler-
assigned child genomes, and complete at least one more generation.

### Required behavior

- The later generation begins from the preceding preferred continuation.
- New child genomes are applied only after that continuation is restored.
- Each controller snapshot matches the genome applied to its worker.
- Lightning DDP again produces a shared gradient while local optimizers again produce
  distinguishable members.
- A later winner again reports one checkpoint with matching producer metadata.

### Failure establishes

The implementation can stage one transfer but cannot repeatedly perform Clan Tuning.

## Contract 12: the same accepted inputs reproduce the same next population

### Setup

Repeat a transition from the same completed candidate states, active genomes, fitness
reports, experiment seed, and supported deterministic settings.

### Required behavior

- The same candidate continuation is persisted.
- The same producer member ID and genome are attached to that checkpoint.
- The same common model state, optimizer history, and training progress are restored.
- The same child genomes are assigned to corresponding next-generation trials.
- The same scheduler mutation and lineage state is committed.
- The first deterministic update of the next generation produces the same resulting
  model states.

### Failure establishes

The transition depends on hidden or unpreserved state rather than its declared training
and scheduler inputs.

## Evidence rule

Executable acceptance evidence must exercise CBT through its supported integration
path. Focused tests may inspect a named lifecycle boundary, but the complete suite must
include a real multi-generation Lightning DDP and Tune workflow that proves the
contracts together.

Design-specific tests may additionally inspect collective membership, controller
snapshot ownership, winner-only checkpoint metadata, scheduler persistence, mutation
lineage, framework callbacks, and version-sensitive Ray seams. Those assertions explain
why the implementation is reliable; they must not replace the black-box training
observations.
