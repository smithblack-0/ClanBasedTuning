# Behavioral test contracts

Status: Milestone 3 behavioral acceptance contract  
Date: 2026-07-31  
Population-resolution clarification: 2026-08-01

## Purpose

These contracts state the observable training behavior ClanBasedTuning must produce.
They treat CBT as a black box around an ordinary Tune and Lightning workflow.

Focused unit and framework tests may protect a selected mechanism, but they are not
substitutes for observing the complete training outcomes. No behavioral contract names
a required collective backend, callback signature, all-gather operation, or integration
module.

## Observable state

The contracts use state an ordinary Tune and Lightning system can expose:

- **model state:** model parameters and persistent buffers;
- **optimizer history:** moments, momentum, counters, and equivalent continuation state;
- **genome:** the controlled subset of a scheduler-assigned `Trial.config`;
- **controller genome snapshot:** an independent copied mapping used only for producer
  provenance;
- **training progress:** global step, epoch or loop state, precision state, and supported
  scheduler state;
- **fitness:** the comparable member-local result supplied to CBT;
- **checkpoint payload:** selected model, optimizer history, and training progress;
- **producer metadata:** schema version, stable member ID, and the genome that produced
  the selected payload; and
- **scheduler transition state:** child genomes, mutation state, lineage, checkpoint
  assignment, and recovery state.

## Contract 1: every round begins from one common continuation

### Setup

Complete a generation whose candidate model, optimizer, and progress states are
distinguishable. Report results so one member is unambiguously preferred. Observe every
member after restore and before the first next-round update.

### Required behavior

- Every member has the preferred candidate's model state.
- Every member has the preferred candidate's optimizer history.
- Every member has the preferred candidate's training progress.
- No losing candidate state survives.
- Member genomes may differ because the scheduler applies one child genome per target
  after the common continuation is restored.

### Failure establishes

The next population did not descend solely from the preferred training trajectory, or
next-round variation was mixed into the inherited continuation.

## Contract 2: child genomes are applied after inheritance

### Setup

Choose a preferred checkpoint whose controlled optimizer values differ from the intended
next-round child genomes. Observe state before and after each target genome is applied,
but before training resumes.

### Required behavior

- Model state and optimizer history restore exactly from the preferred checkpoint.
- The intended child genome is then applied to each target optimizer.
- Only declared controlled fields change.
- Optimizer history is not cleared or recreated.
- Model parameters and training progress do not change during genome application.
- The shared checkpoint is not pre-mutated for one receiver.

### Failure establishes

Mutation occurred before inheritance, one child was baked into the common parent, or
optimizer-history inheritance was destroyed.

## Contract 3: the controller snapshot matches the applied genome

### Setup

Construct one worker from a mutable genome mapping, give the controller its round
snapshot, then mutate the caller's original mapping. Apply the originally assigned
values to the optimizer.

### Required behavior

- The controller owns an independent copied mapping.
- Later mutation of the caller's mapping does not alter the controller snapshot.
- The snapshot equals the controlled values applied for that round.
- The controller does not itself apply or mutate the genome.

### Failure establishes

Producer provenance can drift from the values that produced the result, or the
controller has become a second live genome authority.

## Contract 4: Lightning DDP supplies one shared gradient

### Setup

Run at least two members on distinguishable training examples. Choose a deterministic
update whose unreduced local gradients and expected reduced gradient are known.

### Required behavior

- Corresponding parameters receive the same reduced gradient before the optimizer step.
- That gradient contains every required member's contribution.
- No required member is omitted from the DDP world.
- Optimizer history and genomes remain member-local.

### Failure establishes

Members trained independently, the population was incomplete, or optimizer-side state
was synchronized together with gradients.

## Contract 5: local optimizer behavior produces distinct members

### Setup

Begin from equal model state and equal optimizer history. Supply the same reduced
gradient while assigning controlled values known to produce different updates.

### Required behavior

- Every member begins from equal inherited state.
- Every member receives the same reduced gradient.
- Each optimizer uses its assigned genome.
- Resulting model states differ as predicted.
- Later DDP activity does not erase intended parameter or persistent-buffer divergence.

### Failure establishes

Controlled optimizer behavior was erased, assigned incorrectly, or confused with
different starting states or gradients.

## Contract 6: fitness compares the actual local members

### Setup

Construct distinguishable member states and evaluate them at one common boundary on an
equivalent held-out workload.

### Required behavior

- Each fitness is computed from the model state of the member reporting it.
- Every member is evaluated at the same logical training boundary.
- Examples, transforms, ordering, and metric definition are equivalent.
- Fitness values remain distinct until CBT compares them; they are not reduced into one
  population-wide metric.

### Failure establishes

CBT compared unlike workloads, stale state, different training positions, or an
accidentally reduced fitness signal.

## Contract 7: the preferred member is the sole continuation

### Setup

Complete a generation with distinguishable model state, optimizer history, training
progress, genome, and fitness for each member. Make one member unambiguously preferred.

### Required behavior

- Exactly one continuation checkpoint is retained.
- Its payload matches the preferred member at the evaluated boundary.
- Before reporting, the selected worker attaches producer metadata containing only
  schema version, stable member ID, and its copied genome snapshot.
- Producer metadata matches the scheduler-selected winner and that winner's active
  controlled config.
- Every next member restores that checkpoint.
- No losing continuation is loaded, averaged, or mixed into a receiver.

### Failure establishes

CBT selected or persisted the wrong trajectory, associated it with the wrong genome,
retained multiple parents, or failed to make preference control continuation.

## Contract 8: incomplete producer metadata is never published

### Setup

Cause producer annotation to fail after Lightning constructs the selected payload but
before Tune receives it.

### Required behavior

- The selected worker does not report that checkpoint.
- The scheduler does not accept an unannotated checkpoint as the next parent.
- No next-generation trial begins.
- The failure surfaces at the current boundary.

### Failure establishes

Tune can retain a continuation whose producer cannot be verified, or a half-complete
artifact can become authoritative.

## Contract 9: a partial population cannot choose or advance

### Setup

Cause one required member to fail, omit valid fitness, duplicate identity, or provide an
invalid result while the remaining members reach the boundary.

### Required behavior

- No valid checkpoint-source decision is produced.
- No continuation is accepted as the next parent.
- No member begins another generation.
- The active Clan fails or is invalidated as a whole.
- Waiting work is released by surfaced failure or timeout rather than hanging forever.

### Failure establishes

The implementation can optimize over the wrong population, mix generations, or deadlock
without surfacing the broken boundary.

## Contract 10: one pre-report checkpoint-source result is consistent everywhere

### Setup

Give every required member one valid comparable fitness at the same boundary, including
cases for minimizing, maximizing, and stable ties.

### Required behavior

- Every member reaches a result consistent with the same winning member.
- Exactly one member is permitted to retain and report the checkpoint.
- Repeated local queries return the cached result without repeating population
  synchronization.
- The later scheduler selection agrees with the sole checkpoint-bearing report.

### Failure establishes

Workers can disagree about checkpoint ownership, repeat synchronization unexpectedly,
or report a checkpoint from a member the scheduler did not select.

This contract intentionally does not prescribe whether the implementation communicates
fitness values, a winning ID, or final booleans.

## Contract 11: the scheduler transition is all-or-nothing to workers

### Setup

Interrupt the scheduler after winner verification but before all child genomes,
recovery state, and checkpoint assignments are committed.

### Required behavior

- No target begins from a partial assignment.
- Recovery restores the last completed scheduler generation or fails the experiment.
- Mutation state and lineage do not advance independently of accepted child assignments.
- Every released target has both its intended child genome and the same checkpoint.

### Failure establishes

The scheduler can create mixed generations, duplicate or skip mutation transitions, or
recover from state inconsistent with released trials.

## Contract 12: the lifecycle repeats deterministically

### Setup

Complete at least two real transitions. Repeat one transition from the same accepted
candidate states, active genomes, fitness reports, experiment seed, and supported
deterministic settings.

### Required behavior

- Each later generation begins from the preceding preferred continuation.
- Child genomes are applied only after restore.
- Controller snapshots match applied genomes.
- Shared gradients and optimizer-driven divergence recur.
- A later winner again reports one correctly annotated checkpoint.
- Repeating the same accepted transition selects the same continuation, assigns the same
  child genomes, commits the same scheduler mutation state, and produces the same first
  deterministic updates.

### Failure establishes

The implementation can stage only one transition or depends on hidden, unpreserved
state.

## Evidence rule

Executable acceptance evidence must exercise CBT through its supported integration
path. The complete suite must include a real multi-generation Lightning DDP and Tune
workflow.

Focused tests may inspect controller snapshot ownership, cached source decisions,
producer metadata, scheduler persistence, mutation lineage, and version-sensitive
framework seams. A fake callback proves only local code behavior. It does not prove a
production population-resolution mechanism.
