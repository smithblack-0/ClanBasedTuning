# Behavioral test contracts

Status: Milestone 3 behavioral acceptance contract  
Date: 2026-07-31

## Purpose

These contracts state the training behavior that ClanBasedTuning must produce.
They deliberately treat CBT as a black box around an ordinary distributed
training job. A test may provide fitness to CBT and inspect the resulting model,
optimizer, training progress, checkpoint artifacts, and later training behavior.
It may not require an internal winner ID, controller field, callback order,
scheduler method, comparison vocabulary, or framework-private object merely to
make the assertion convenient.

The distinction is:

- **Behavioral:** report results to CBT such that one variant is unambiguously
  preferred, then observe that the next round begins from that variant.
- **Premature implementation contract:** configure a named metric with a named
  `min` or `max` option, inspect an internal winner flag, or call a policy method
  directly.

The selected design will need additional framework-contract and unit tests. Those
protect the mechanism used to deliver these outcomes; they are not substitutes
for observing the outcomes themselves.

## Observable training state

The contracts use only state that an ordinary training system can expose:

- **model state:** model parameters and persistent model buffers;
- **optimizer history:** accumulated optimizer tensors, counters, moments,
  momentum, and equivalent state, excluding the controlled values newly assigned
  for an upcoming round;
- **controlled optimizer values:** the optimizer hyperparameters CBT varies
  between variants;
- **training-progress state:** framework continuation state such as the global
  step, epoch or loop progress, precision state, and supported scheduler state;
- **fitness:** the result supplied to CBT for comparing one completed variant with
  the others; and
- **checkpoint:** the persisted continuation artifact from which training can be
  restored.

## Contract 1: every round begins from one common continuation

### Setup

Arrange a preceding round whose candidate states are distinguishable. Report
results to CBT so one candidate is unambiguously preferred. Observe every variant
at the beginning of the next round, after restoration and before its first
training update.

### Required behavior

- Every variant has the preferred candidate's model state.
- Every variant has the preferred candidate's optimizer history.
- Every variant has the preferred candidate's training-progress state.
- No distinguishable model, optimizer-history, or progress value from a losing
  candidate survives.
- Controlled optimizer values may differ between variants because next-round
  variation is applied after the common continuation is restored.

### Failure establishes

The next population did not descend solely from the preferred training
trajectory, or next-round variation was incorrectly mixed into the inherited
continuation.

## Contract 2: next-round variation is applied after inheritance

### Setup

Choose a preferred candidate whose checkpoint contains controlled optimizer
values distinguishable from the values CBT will assign in the next round.
Observe the restored state before and after next-round controlled values are
applied, but before a training update.

### Required behavior

- Model state and optimizer history first restore exactly from the preferred
  candidate.
- CBT then assigns the intended controlled values for each new variant.
- Applying those values changes only the declared optimizer fields.
- Applying them does not recreate the optimizer, clear its history, change model
  parameters, or advance training progress.
- The persisted preferred checkpoint is not already mutated for one receiver's
  next-round role.

### Failure establishes

Mutation occurred before inheritance, one receiver's mutation was baked into the
common parent, or optimizer-history inheritance was destroyed while applying the
new values.

## Contract 3: Lightning DDP supplies one shared gradient

### Setup

Run at least two variants on different training examples. Choose a deterministic
update for which their unreduced local gradients are distinguishable and the
expected reduced gradient is known.

### Required behavior

- Immediately before the optimizer update, corresponding trainable parameters in
  every variant have the same reduced gradient.
- That gradient contains the required contribution from every active variant.
- No required variant is queued or omitted from the tested collective.
- Optimizer history and controlled optimizer values remain local; only the
  gradient is shared at this boundary.

### Failure establishes

The variants trained independently, the active population was incomplete, or
optimizer-side state was synchronized together with the gradient.

## Contract 4: local optimizer behavior produces the variants

### Setup

Begin a deterministic update from equal model state and equal optimizer history.
Use the same reduced gradient while assigning controlled optimizer values known
to produce different updates.

### Required behavior

- Every variant begins from equal model state and optimizer history.
- Every variant receives the same reduced gradient.
- Each optimizer uses the controlled values assigned to that variant.
- The resulting model states differ as predicted by those optimizer updates.
- Later Lightning DDP activity does not overwrite the intended parameter or
  persistent-buffer divergence.

### Failure establishes

The controlled optimizer behavior was erased, assigned incorrectly, or confused
with divergence caused by different starting state or different gradients.

## Contract 5: fitness compares the actual local variants

### Setup

Construct variants whose local model states produce distinguishable evaluation
results. Evaluate them at one common round boundary on the same held-out workload
under equivalent conditions.

### Required behavior

- Each fitness value is computed from the model state of the variant reporting it.
- Every variant is evaluated at the same logical training boundary.
- The held-out examples, transforms, ordering rules, and metric definition are
  equivalent within the supported configuration.
- Candidate fitness values remain distinct when CBT compares them; they are not
  averaged into one population-wide result.

### Failure establishes

CBT compared unlike workloads, stale or foreign model state, different training
positions, or a fitness signal erased by distributed reduction.

## Contract 6: the preferred variant is the one continued

### Setup

Complete a round with distinguishable model state, optimizer history, and
training progress for each variant. Report results to CBT such that one variant is
unambiguously preferred.

### Required behavior

- Exactly one continuation checkpoint is retained for the transition.
- Its model state, optimizer history, and training progress match the preferred
  variant at the evaluated round boundary.
- The next round restores that checkpoint into every variant.
- No losing continuation is loaded, averaged, or mixed into any receiver.

### Failure establishes

CBT selected or persisted the wrong training trajectory, retained multiple
competing parents, or failed to make the reported preference control the next
round.

The contract does not prescribe how preference is configured or represented.

## Contract 7: a partial population cannot advance

### Setup

Cause one required variant to fail or omit its valid fitness while the remaining
variants reach the round boundary.

### Required behavior

- No continuation checkpoint is accepted as the next parent.
- No variant begins another round.
- The active Clan fails or is invalidated as a whole rather than silently
  continuing with fewer participants.
- Waiting work is released by a surfaced failure rather than hanging indefinitely.
- The failure provides enough context to identify the broken round or population.

### Failure establishes

The implementation can optimize over a population different from the configured
Clan, enter a mixed generation, or deadlock without reporting collective failure.

## Contract 8: the lifecycle repeats

### Setup

Complete a round, transition through the preferred checkpoint, and complete at
least one more round.

### Required behavior

- The later round begins from the preceding preferred continuation.
- New controlled values are applied only after that continuation is restored.
- Lightning DDP again produces a shared gradient while the local optimizers again
  produce distinguishable variants.
- The later variants produce comparable local fitness values.
- A later reported preference again determines the sole continuation.

### Failure establishes

The implementation can stage one transfer but cannot repeatedly perform Clan
Tuning.

## Contract 9: the same accepted inputs reproduce the same next population

### Setup

Repeat a transition from the same completed candidate states, fitness reports,
experiment seed, and supported deterministic settings.

### Required behavior

- The same candidate continuation is persisted.
- The same common model state, optimizer history, and training progress are
  restored.
- The same controlled optimizer values are assigned to corresponding next-round
  variants.
- The first deterministic update of the next round produces the same resulting
  model states.

### Failure establishes

The transition depends on hidden or unpreserved state rather than its declared
training inputs.

## Evidence rule

Executable acceptance evidence must exercise CBT through its supported
integration path. Focused tests may inspect a named lifecycle boundary, but the
complete suite must include a real multi-round Lightning DDP and Tune workflow
that proves the contracts together.

Design-specific tests may additionally inspect collective membership, checkpoint
injection, scheduler state, controller serialization, framework callbacks, and
version-sensitive Ray seams. Those assertions explain why the implementation is
reliable; they must not replace the black-box training observations above.
