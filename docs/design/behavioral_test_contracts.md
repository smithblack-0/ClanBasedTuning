# Behavioral test contracts

Status: Milestone 3 behavioral acceptance contract  
Date: 2026-07-31

## Purpose

These contracts state the observable training behavior ClanBasedTuning must produce.
They deliberately separate externally meaningful behavior from one provisional class,
callback, or Ray collective primitive.

Focused unit and framework tests protect the mechanisms used to produce these outcomes;
they are not substitutes for observing the complete workflow.

## Observable state

The contracts use state that an ordinary Tune and Lightning system can expose:

- **stable member ID:** the persistent Clan identity associated with one live Tune trial;
- **model state:** model parameters and persistent model buffers;
- **optimizer history:** accumulated optimizer tensors, counters, moments, momentum, and
  equivalent state, excluding newly assigned controlled values;
- **genome:** the controlled subset of the current Tune trial configuration assigned by
  the CBT scheduler;
- **controller genome snapshot:** an independently copied mapping used only for winner
  provenance;
- **training-progress state:** Lightning continuation state such as global step, epoch,
  loop progress, precision state, and supported scheduler state;
- **fitness:** the local comparable result for one completed member;
- **population-resolution result:** the stable member selected through the Ray
  collective before Tune reporting;
- **checkpoint payload:** the selected model, optimizer history, and training-progress
  continuation;
- **checkpoint producer metadata:** schema version, stable member ID, and copied genome
  that produced the selected payload; and
- **scheduler transition state:** child genomes, mutation random state, lineage,
  checkpoint assignment, and recovery state for the next generation.

## Contract 1: every generation begins from one common continuation

### Setup

Arrange a preceding generation whose candidate states are distinguishable. Report
results so one candidate is unambiguously preferred. Observe every member after
restoration and before its first new training update.

### Required behavior

- Every member has the preferred candidate's model state.
- Every member has the preferred candidate's optimizer history.
- Every member has the preferred candidate's training-progress state.
- No distinguishable continuation state from a losing candidate survives.
- Genomes may differ because the scheduler assigns one target genome per trial after the
  common continuation is restored.

### Failure establishes

The next population did not descend solely from the selected training trajectory, or
next-generation variation was mixed into the inherited continuation.

## Contract 2: child genomes are applied after inheritance

### Setup

Choose a selected candidate whose checkpoint contains controlled optimizer values that
differ from the child genomes assigned in the next generation. Observe state before and
after the target `Trial.config` is applied, but before a training update.

### Required behavior

- Model state and optimizer history first restore exactly from the selected candidate.
- CBT then applies the intended child genome for each target member.
- Applying that genome changes only declared optimizer fields.
- Applying it does not recreate the optimizer, clear its history, change model
  parameters, or advance training progress.
- The shared checkpoint is not pre-mutated for one receiver's child role.

### Failure establishes

Mutation occurred before inheritance, one receiver's child genome was baked into the
common parent, or optimizer-history inheritance was destroyed.

## Contract 3: the controller owns the genome mapping it records

### Setup

Construct one controller from a mutable genome mapping, then mutate the caller's mapping
before checkpoint annotation.

### Required behavior

- The controller retains an independently copied mapping.
- Later top-level mutation of the caller's mapping does not alter the controller copy.
- The copied values equal the controlled values applied to the optimizer for that
  generation.
- The controller does not itself apply or mutate the genome.

The contract does not claim recursive immutability for arbitrary nested values unless a
later supported genome schema requires and proves it.

### Failure establishes

Checkpoint provenance can drift from the values that produced the result, or the
controller has become a second live genome authority.

## Contract 4: Lightning DDP supplies one shared gradient

### Setup

Run at least two members on different training examples. Choose a deterministic update
for which unreduced local gradients are distinguishable and the expected reduced
gradient is known.

### Required behavior

- Immediately before the optimizer update, corresponding trainable parameters in every
  member have the same reduced gradient.
- That gradient contains the required contribution from every active member.
- Optimizer history and genomes remain local; only the gradient is shared at this
  boundary.

### Failure establishes

The members trained independently, the active population was incomplete, or optimizer-
side state was synchronized together with the gradient.

## Contract 5: local optimizer behavior produces distinct members

### Setup

Begin a deterministic update from equal model state and optimizer history. Use the same
reduced gradient while assigning genomes known to produce different updates.

### Required behavior

- Every member begins from equal model state and optimizer history.
- Every member receives the same reduced gradient.
- Each optimizer uses the values assigned through that member's genome.
- Resulting model states differ as predicted by those optimizer updates.
- Later Lightning DDP activity does not overwrite intended parameter or persistent-
  buffer divergence.

### Failure establishes

The genome was erased, assigned incorrectly, or confused with divergence caused by a
different starting state or gradient.

## Contract 6: fitness describes the actual local member

### Setup

Construct members whose local model states produce distinguishable evaluation results.
Evaluate them at one common round boundary on equivalent held-out workloads.

### Required behavior

- Each fitness is computed from the state of the member contributing it.
- Every member is evaluated at the same logical training boundary.
- Held-out examples, transforms, ordering rules, and metric definitions are equivalent.
- Fitness values remain distinct until the Ray population-resolution boundary; they are
  not averaged into one Lightning metric.

### Failure establishes

CBT compared unlike workloads, stale or foreign state, different training positions, or
a fitness signal erased by distributed reduction.

## Contract 7: Ray population resolution includes the complete Clan

### Setup

Run one qualifying boundary with a fixed configured population and distinguishable local
fitness values.

### Required behavior

- Every configured stable member participates exactly once.
- Every contributed fitness is associated with the correct stable member.
- No member from another generation is admitted.
- Every participant receives the same selected stable member ID.
- The selected member matches the shared deterministic comparison and tie policy.
- Exactly one local controller caches `True` for checkpoint retention.

The contract does not require a particular Ray collective primitive or require the
controller to receive the complete fitness population rather than the selected member.

### Failure establishes

Population membership, identity, generation isolation, agreement, or policy application
is incorrect.

## Contract 8: repeated save queries do not repeat population resolution

### Setup

After one successful Ray population-resolution boundary, query the selected and losing
controllers more than once and later invoke the provenance guard.

### Required behavior

- Every query returns the same local decision.
- No query performs another Ray collective operation.
- Provenance writing reads the cached decision only.

### Failure establishes

A seemingly local checkpoint guard can deadlock or desynchronize the population by
entering an unexpected second collective.

## Contract 9: incomplete population resolution fails the generation

### Setup

Cause one required member to fail, omit its fitness, duplicate an identity, contribute
invalid data, or enter with a mismatched generation operation.

### Required behavior

- No member receives a valid checkpoint-source decision.
- No continuation checkpoint is accepted as the next parent.
- No member begins another generation.
- Waiting work is released through a surfaced failure or timeout rather than hanging
  indefinitely.
- The failure identifies the broken population boundary sufficiently for diagnosis.

### Failure establishes

The implementation can optimize over a population different from the configured Clan,
select from malformed data, enter a mixed generation, or deadlock silently.

## Contract 10: the selected member is the one continued

### Setup

Complete a generation with distinguishable model state, optimizer history, training
progress, active genome, and fitness for every member.

### Required behavior

- Worker-side Ray population resolution and scheduler verification select the same stable
  member.
- Exactly one continuation checkpoint is retained.
- Its payload matches the selected member's model, optimizer history, and training
  progress at the evaluated boundary.
- No losing continuation is loaded, averaged, or mixed into a receiver.
- Every next member restores the selected checkpoint.

### Failure establishes

Worker coordination and scheduler policy disagree, or the wrong training trajectory is
continued.

## Contract 11: producer metadata is complete before publication

### Setup

Allow the selected worker to construct its Lightning checkpoint. Exercise both a
successful producer annotation and a forced annotation failure before `tune.report()`.

### Required behavior

On success:

- metadata contains only the accepted namespace, schema version, selected stable member
  ID, and copied current genome;
- metadata member and genome match the scheduler-selected winner and its active
  `Trial.config`;
- unrelated metadata and checkpoint payload remain unchanged; and
- the complete annotated checkpoint is reported.

On failure:

- the checkpoint is not reported;
- the scheduler does not accept an unannotated continuation; and
- no next generation begins.

### Failure establishes

Tune can retain a continuation whose producer cannot be verified, or metadata writing
changes training payload state.

## Contract 12: the scheduler transition is all-or-nothing to workers

### Setup

Interrupt the scheduler after winner verification but before all child genomes,
recovery state, and checkpoint assignments are committed.

### Required behavior

- No target begins the next generation from a partial assignment.
- Recovery restores the last completed scheduler generation or fails the experiment.
- Mutation random state and lineage do not advance independently of accepted child
  assignments.
- Every released target has both its intended child genome and the same selected
  checkpoint.

### Failure establishes

The scheduler can create mixed generations, duplicate or skip mutation transitions, or
recover from hidden state inconsistent with released trials.

## Contract 13: the lifecycle repeats

### Setup

Complete one generation, transition through the selected checkpoint and scheduler-
assigned child genomes, and complete at least one more generation.

### Required behavior

- The later generation begins from the preceding selected continuation.
- New child genomes are applied only after restoration.
- Each controller snapshot matches the genome applied to its member.
- Lightning DDP again produces a shared gradient while local optimizers again produce
  distinguishable members.
- Ray population resolution again identifies one checkpoint source.
- A later winner again reports one checkpoint with matching producer metadata.

### Failure establishes

The implementation can stage one transfer but cannot repeatedly perform Clan Tuning.

## Contract 14: accepted deterministic inputs reproduce the next population

### Setup

Repeat a transition from the same completed member states, active genomes, fitness,
experiment seed, membership mapping, and supported deterministic settings.

### Required behavior

- The same stable member is selected by worker and scheduler paths.
- The same continuation is persisted.
- The same producer member ID and genome are attached.
- The same child genomes are assigned to corresponding target members.
- The same scheduler mutation and lineage state is committed.
- The first deterministic update of the next generation produces the same states.

### Failure establishes

The transition depends on hidden or unpreserved state rather than declared inputs.

## Evidence rule

Executable acceptance evidence must exercise CBT through its supported integration path.

Framework-independent tests may use fakes to protect local controller caching or pure
selection. Those tests must state that they do not qualify Ray collective behavior.

The complete suite must include direct pinned-Ray population-resolution contracts and a
real multi-generation Lightning DDP and Tune workflow that proves the contracts
together.
