# ClanBasedTuning system architecture

Status: proposed design under human review  
Date: 2026-07-31  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Design result

ClanBasedTuning composes one Tune trial per Clan member into one externally
launched Lightning DDP job. PyTorch DDP supplies one reduced gradient to every
member. Each member applies that gradient through its own optimizer history and
controlled hyperparameters.

At a qualifying Lightning validation boundary, each process publishes its local
result, receives the same complete population, and advances its existing
`ClanController`. The selected member publishes the sole candidate continuation
checkpoint. Every member reports the same selected parent and its own next
controller state to Tune. A narrow Tune scheduler pauses each reporting trial,
verifies the complete population of proposals, and assigns the winner checkpoint
together with each receiver's own controller state through Ray's native trial
lifecycle.

The next generation starts in replacement trial processes. Lightning restores
the winner's continuation state. The receiving `ClanController` is restored from
the target trial configuration, and ClanBasedTuning reapplies the configuration
returned by that controller without replacing inherited optimizer history. The
population reforms DDP and continues.

This design introduces no second training loop, checkpoint format, optimizer
factory, population policy, or gradient collective.

## Scope and non-scope

This document fixes the proposed responsibility and lifecycle model needed to
judge implementation work. It does not yet:

- fix the final ordinary-user facade;
- divide implementation into milestone-sized PRs;
- define the complete Milestone 5 optimizer-resolution language;
- claim accelerator, multi-node, restoration, or sharding support without direct
  evidence; or
- accept historical integration code as an implementation foundation.

The [behavioral test contracts](behavioral_test_contracts.md) govern the outcomes
this design must make observable. The roadmap and accepted project decisions
remain authoritative for product meaning and framework ownership.

## Central invariants

1. One Tune trial is one stable Clan member.
2. Every required member is concurrently resident before shared-gradient
   training begins.
3. One externally launched process in each trial is one DDP rank.
4. Lightning owns the training, validation, optimizer, and checkpoint lifecycle.
5. PyTorch DDP owns model wrapping and gradient reduction.
6. One `ClanController` persists with each member's control state and remains the
   sole population-policy implementation.
7. Every controller consumes the same complete ordered population and must reach
   the same winner.
8. Ray executes checkpoint and target-state assignment; it does not select the
   winner or mutate optimizer values.
9. The winner supplies continuation state. The receiver supplies member identity
   and controller state, from which its next controlled configuration is read.
10. A partial or corrupt population cannot select, inherit, resume, or continue.
11. No process that reported the end of round \(r\) may resume old-process
   training as round \(r+1\).

## State ownership

| State | Authoritative owner | Transition behavior |
| --- | --- | --- |
| Model parameters and persistent buffers | Lightning checkpoint produced from the winning member's live model | Copied from the selected winner to every next-generation member. |
| Optimizer tensors, counters, moments, and momentum | Lightning checkpoint produced from the selected winner | Restored from the winner before receiving controlled values are reapplied. |
| Lightning loop and training-progress state | Lightning checkpoint | Restored from the winner to every receiver. |
| Controlled optimizer values for the current round | Receiving member's `ClanController` state | Remain target-local and are read from the restored controller after optimizer restoration. |
| Member identity | Ray trial configuration in the reserved Clan namespace | Never copied from the winner. |
| Controller random stream and next-round state | Receiving member's post-decision controller state | Remain target-local and travel in the target trial configuration, not the winner checkpoint. |
| Complete round population | Round exchange, derived from one result per configured member | Exists only long enough for every local controller to consume the same immutable population. |
| Winner and next controller states | Each local `ClanController`; agreement on the winner is verified by the scheduler | The scheduler executes the agreed result but does not recompute policy. |
| Trial actor, process group, device assignment, pause, and resume | Ray Tune and Lightning/PyTorch | Recreated or resumed by the frameworks; never serialized as Clan state. |

The split between the winner checkpoint and target trial configuration is
fundamental. Copying the winner's complete trial configuration or controller state
would collapse member identity and mutation streams. Storing target-local control
state inside the Lightning checkpoint would make Ray's winner-checkpoint
assignment overwrite every receiver with the winner's controller state.

The next controlled configuration is not an independent state authority. It is
the `config` projection of the target's post-decision `ClanController` state. A
transition report may repeat that projection for diagnostics, but implementation
must verify it against the controller state rather than treating both as writable
sources of truth.

## Runtime records

The integration needs two small plain-data records. Names remain provisional, but
their information boundaries are part of the design.

### Round result record

A round result record contains:

- experiment or Clan identity;
- member identity;
- completed round index;
- controlled configuration used in that round; and
- finite member-local fitness.

It contains no model tensors, optimizer tensors, checkpoint path, Ray `Trial`, or
live callback. The member integration converts between this record and the
existing `ClanRound` object at the controller callback boundary.

### Transition report

A transition report contains:

- member identity;
- completed and next round indices;
- member-local fitness;
- selected winner identity;
- the receiving member's post-decision controller state; and
- a winner continuation checkpoint only when the reporting member is the selected
  winner.

The report contains target control continuation and candidate training
continuation as separate fields. The scheduler accepts the checkpoint only from
the unanimously selected member. It assigns each report's controller state only
to that report's target member.

An optional flattened configuration projection may be included for logging and
review, but it is derived from the controller state and cannot override it.

## Components

### Existing `ClanController`

**Main idea:** advance one member's evolutionary policy from one complete
population.

The controller continues to own:

- one member's current `ClanRound`;
- completeness validation for the population it receives;
- `min` or `max` winner selection;
- target-local mutation;
- target-local random state; and
- production of the member's next controlled configuration.

It does not own Ray trials, rendezvous, DDP, checkpoints, optimizer objects,
Lightning callbacks, or failure fan-out.

The integration supplies its three existing effects:

- `save_member_fitness` converts and publishes one round result;
- `load_population` waits for and reconstructs one complete ordered population;
- `select_winner` records the local winner for the later transition report.

No second controller runs in the Tune driver or scheduler.

### Round exchange

**Main idea:** accept one result from every configured member and expose the same
immutable population to every member.

The proposed implementation is a small asynchronous Ray actor created once per
Clan run. It exposes two operations aligned with the accepted controller
callbacks:

1. `publish(round_result)` accepts one member's completed result and returns as
   soon as the record is validated and stored.
2. `wait_population(round_index)` waits until the active round contains exactly
   one valid result for every configured member, then returns the same ordered
   population snapshot to every caller.

The actor:

- verifies Clan identity, member identity, and round identity;
- rejects duplicate or stale publications;
- orders the completed population by stable member identity;
- releases all waiting members with the same population snapshot;
- retains no policy, checkpoint, model, optimizer, or mutation behavior; and
- can be aborted by the Tune-side lifecycle owner when a member fails.

The actor must be asynchronous or use an equivalent concurrency mechanism so
waiting calls do not prevent later publications from executing.

The exchange is transport and rendezvous, not a second population authority.
Expected membership is derived from the same Tune trial construction that defines
the live Clan. Its validation protects the transport boundary; the controller's
own completeness guard protects the policy boundary.

This exchange replaces the rejected approach of reporting to Tune first and then
using a private Tune controller task API to invoke code inside stopped trial
actors. Each member now advances its own controller through ordinary actor code
before emitting its transition report.

### Clan cluster environment

**Main idea:** present externally created Tune trial processes to Lightning as
one DDP world.

A focused Lightning `ClusterEnvironment` implementation supplies:

- `creates_processes_externally = True`;
- global rank equal to stable member identity;
- local rank zero for the one process owned by each trial;
- world size equal to the configured population;
- a common rendezvous address and port; and
- validation that the Trainer's one-device-per-process settings agree with the
  Clan world.

The environment does not launch processes, reserve Ray resources, form Tune
trials, wrap the model, or transfer checkpoints.

For the first manual composition, the rendezvous endpoint may be explicitly
provided for a dedicated single-node run. Automated allocation and broader
cluster topology belong to later usability and support qualification; the rank
and ownership model does not depend on how the endpoint is manufactured.

### Clan DDP strategy

**Main idea:** specialize Lightning DDP only where one rank is also one
divergent, independently checkpointed Clan member.

The strategy extends Lightning's `DDPStrategy` and delegates ordinary process
group creation, model wrapping, gradient buckets, backward synchronization,
barriers, device placement, and optimizer lifecycle to Lightning and PyTorch.
Its justified differences are:

1. It uses the externally created Clan cluster environment.
2. It constructs DDP with initial synchronization enabled so a fresh round starts
   from one model state.
3. It disables per-forward buffer broadcast. PyTorch DDP does not broadcast
   parameters after initialization, but its default buffer broadcast would copy
   rank-zero persistent buffers into every member on each forward and erase part
   of intended model divergence.
4. It permits the selected rank to write a complete Lightning checkpoint to its
   trial-local path at the round boundary. Lightning's ordinary DDP strategy
   writes only on global rank zero because ranks normally represent replicas of
   one model; the selected Clan member may be any rank.

The rank-local checkpoint change remains inside the Lightning strategy and
`CheckpointIO` lifecycle. It does not introduce a Clan checkpoint format or call
`torch.save` on an independently assembled state dictionary.

The strategy does not synchronize optimizer history or parameters after optimizer
updates. It relies on native DDP gradient reduction and explicitly tests that the
framework configuration preserves divergence.

### Optimizer-configuration applier

**Main idea:** apply the receiving controller's declared controlled values to
already constructed and restored optimizer objects.

The lifecycle position is fixed even though the complete Milestone 5 rule system
is not:

1. Lightning constructs the user's optimizer objects.
2. Lightning restores the winner's optimizer history from the assigned
   checkpoint.
3. ClanBasedTuning restores the target's controller state from the Tune config.
4. On the first training-start hook after restoration, the applier obtains the
   current controlled configuration from `controller.get_config()` and writes
   those values to the supported optimizer fields.
5. Training begins only after application succeeds.

The applier must not construct optimizers, replace optimizer state dictionaries,
or interpret the user's full Tune configuration as an optimizer schema. The
initial manual workflow may qualify one explicit optimizer and direct field
mapping. The later optimizer-utility design can generalize targeting and
remapping without changing this lifecycle boundary.

The selected Lightning hook must be proven by a framework-contract test to occur
after optimizer restoration and before the first optimizer update. A hook that
runs before `restore_training_state()` is invalid because the restored checkpoint
would overwrite the receiving values.

### Round-boundary callback

**Main idea:** close one local Lightning round and emit one complete transition
report.

At the accepted validation boundary, the callback performs this sequence:

1. Ignore Lightning sanity checking and any validation event not configured as a
   Clan boundary.
2. Read the configured fitness metric from the member's local Lightning metrics
   without distributed metric reduction.
3. Enter a DDP barrier so every member has completed equivalent validation work.
4. Call `controller.set_fitness()`. Its save callback publishes the local round
   result to the exchange and returns after publication is accepted.
5. Call `controller.advance()`. Its load callback waits for the complete
   population and reconstructs the controller input.
6. Capture the local winner and post-decision controller state.
7. If this member is the selected winner, ask Lightning to save one checkpoint to
   the trial-local checkpoint directory. Losing members do not serialize their
   continuation state.
8. Report transition metadata and the optional winner checkpoint through Tune's
   reporting API.

The callback does not train, validate, select the winner, mutate values, assign a
checkpoint to another trial, or apply the next configuration to the current
optimizer. The reported process is at the end of the old round. Ray must pause
that trial; the next process reads its configuration only after restoring the
selected checkpoint.

The callback must not serialize its controller or member-local control state into
Lightning callback state. Its Lightning checkpoint contribution is empty unless
a later accepted design identifies genuinely winner-owned callback state.

### Tune member adapter

**Main idea:** bridge one Ray function trial to one ordinary Lightning
`Trainer.fit()` call.

The adapter:

- reads the reserved Clan namespace and restores the target-local controller;
- obtains any assigned Ray checkpoint through the function-trial checkpoint API;
- exposes that checkpoint directory to Lightning as the `ckpt_path` for the one
  `Trainer.fit()` call;
- constructs or receives the concrete integration components described here;
- calls the user-owned model, data, optimizer, and Trainer construction path; and
- never implements a batch, epoch, validation, or optimizer loop.

For a resumed generation, the adapter keeps the Ray checkpoint materialized for
the duration of `Trainer.fit()`. For a fresh generation, it passes no checkpoint.
The adapter does not parse a class-`Trainable` checkpoint or require the user to
implement `setup`, `step`, `save_checkpoint`, `load_checkpoint`, or
`reset_config`.

Actor reuse is disabled for the initial supported path. Every next generation is
constructed in a replacement process from the target trial configuration and the
assigned winner checkpoint. This prevents a suspended old Lightning call from
continuing with stale in-process state or requiring FunctionTrainable
`reset_config` semantics.

### Clan Tune scheduler

**Main idea:** verify and execute one complete, unanimous Clan transition through
Ray's native trial lifecycle.

For every transition report, the scheduler records the report and returns the
normal `PAUSE` action. It never returns `CONTINUE` for a completed Clan boundary.
Thus each old-generation trial is paused before it can execute further Lightning
work. Result buffering is disabled.

When every configured member is paused at the same boundary, the scheduler
verifies:

- exactly one report per configured member;
- one completed round identity;
- one next round identity;
- one agreed winner;
- stable target member identities;
- one valid target-local controller state per member;
- exactly one continuation checkpoint; and
- that the checkpoint was reported by the agreed winner.

It then:

1. preserves every target trial's user configuration and stable member identity;
2. replaces only the target's controller state and next-round metadata inside the
   reserved Clan namespace;
3. assigns the winner checkpoint as every target's next continuation checkpoint;
4. marks the complete next generation ready only after every target assignment is
   prepared; and
5. allows Ray to schedule the paused targets, which start replacement trial
   processes and restore through the member adapter.

The scheduler does not compare fitness, invoke mutation, construct controller
state, save Lightning checkpoints, or manage a process group.

Ray's public scheduler result contract provides `CONTINUE`, `PAUSE`, and `STOP`.
Ray 2.56 does not expose complete cross-trial checkpoint reassignment as a stable
high-level public method. The implementation may therefore require the same
narrow version-sensitive controller and checkpoint-manager seam used by Ray's PBT
scheduler after the trials are paused. That seam must remain isolated in this
class, covered by a direct Ray framework-contract test, and pinned to the
qualified Ray version. It must not leak into controller, Lightning, or user APIs.

Standard `PopulationBasedTraining` is not itself the policy implementation for
this design. Its quantile selection, donor choice, target-config copying, and
mutation behavior conflict with sole-parent Clan policy and target identity. The
Clan scheduler may reuse Ray lifecycle mechanisms demonstrated by PBT, but not its
population policy.

## Reserved Tune configuration namespace

ClanBasedTuning requires a package-owned nested namespace inside each Tune trial
configuration. The exact key is an implementation detail, but its contents and
update rule are architectural:

- stable Clan or experiment identity;
- stable member identity;
- population size;
- current round identity;
- round-exchange reference or name;
- DDP rendezvous specification; and
- target-local controller state.

The current controlled optimizer configuration is available through the
controller state and is not stored as a second writable field.

User experiment configuration remains outside this namespace. A generation
transition updates only the target's reserved Clan values. It never copies the
winner's complete Tune config onto another member.

The user-facing model or workload builder should receive the user's configuration
without package control metadata unless the user explicitly requests access to
it.

## Complete lifecycle

### 1. Driver construction and admission

The Tune driver creates exactly one trial configuration per member identity and
one round exchange for the Clan. It configures the custom scheduler, disables
actor reuse, and requires `max_concurrent_trials` equal to the population size.

Before starting, the manual workflow verifies that the dedicated Ray environment
has sufficient resources for the entire population. The implementation must not
rely on PBT-style time multiplexing because a queued member would be absent from
DDP gradient reduction.

Atomic reservation across independent Tune trials is not claimed by this initial
architecture. The first supported path therefore requires a dedicated or
otherwise reserved resource envelope and fails preflight when declared resources
are insufficient.

### 2. Member process construction

Each trial process enters through the Tune member adapter. It reads its stable
identity and target-local controller state from the reserved config and obtains
any assigned Ray checkpoint. It constructs:

- its local `ClanController`;
- callbacks adapting controller publication and loading to the round exchange;
- the external cluster environment;
- the Clan DDP strategy;
- the optimizer-configuration applier; and
- the round-boundary callback.

The user's ordinary Lightning module, dataloaders, optimizer construction, and
Trainer choices remain user- and Lightning-owned. The adapter calls one ordinary
`Trainer.fit()` and contains no training loop of its own.

### 3. Initial state

For a fresh run, native DDP initialization synchronizes model parameters and
persistent buffers. Every optimizer begins from the same empty or explicitly
provided history, after which each member's initial controller configuration is
applied.

For a seeded or resumed run, every member receives the same initial Lightning
checkpoint through Ray. The member adapter passes the checkpoint to Lightning.
Lightning restores the common continuation state before target-local controller
configuration is applied.

### 4. Shared-gradient training

Every member processes its own training partition. DDP reduces gradients across
the complete world. Each member then applies the common reduced gradient through
its own optimizer history and controlled values.

DDP parameter synchronization after initialization and forward-time buffer
broadcast are not allowed to erase the resulting divergence. Model structure,
parameter registration order, and gradient-producing computation must remain
compatible across members.

### 5. Comparable validation

The manual integration disables Lightning's automatic distributed sampler
replacement and supplies:

- a training sampler partitioned by member rank; and
- a validation loader that presents the same held-out workload to every member.

Fitness metrics remain local. `sync_dist=True`, cross-rank metric reduction, and
validation sharding are invalid for the selection metric because they erase or
change the candidate comparison.

All members use equal validation length and a common round boundary. Unsupported
uneven-input or early-exit behavior fails rather than relying on DDP join
semantics that would redefine the active population.

### 6. Local population decision

After validation and a DDP barrier, every member publishes one round result to
the exchange and receives the same ordered population through its controller
callbacks. Every process-local controller advances from that population.

The controllers are expected to produce one winner and one target-local next
controller state per member. Scheduler-side agreement checking is a corruption
and consistency guard, not a second policy vote.

### 7. Winner checkpoint and Tune report

Only the member selected by its local controller asks Lightning to serialize its
continuation state. Every member reports its fitness, selected winner, and
post-decision target controller state. The winner also reports the Lightning
checkpoint through Tune.

If local controllers disagree, zero or multiple checkpoints may be reported; the
scheduler rejects the transition before assignment. Correct unanimous execution
produces exactly one checkpoint without serializing losing trajectories.

### 8. Pause and sole-parent assignment

The scheduler returns `PAUSE` for each report. After every member is paused at the
same boundary, it verifies the reports and assigns the sole winner checkpoint to
every target while preserving each target identity and installing its own
post-decision controller state.

A failure before all assignments are prepared leaves the old round as the last
complete authoritative generation. No paused target is selected to run until the
complete next generation is ready.

### 9. Replacement, restore, and reconciliation

Ray schedules each paused target as a replacement process because actor reuse is
disabled. The member adapter receives the assigned winner checkpoint and passes it
to Lightning. Lightning restores model state, optimizer history, and training
progress. The target controller is restored from that target's Tune configuration.
The optimizer applier then reads the controller's configuration and writes those
controlled values into the restored optimizer without reconstructing it or
clearing history.

### 10. Reformation and continuation

The complete target population reforms the DDP world, verifies common
continuation state, and begins the next round. The same lifecycle repeats until a
synchronized population boundary satisfies the configured completion rule.

## Failure and completion

### Member failure before the boundary

Ray reports the failed trial to the Clan scheduler. The scheduler marks the
active round invalid, aborts the round exchange so members blocked in population
loading are released, and stops or invalidates every remaining member. Members
blocked in DDP are terminated through Ray's trial lifecycle. No partial population
decision or next-generation assignment is allowed.

### Corrupt or disagreeing reports

Duplicate member IDs, wrong rounds, missing or multiple checkpoints,
inconsistent winners, or malformed target controller state fail before checkpoint
assignment. The previous round remains the last complete authoritative
generation.

### Failure during assignment

The scheduler prepares all target assignments before allowing any next-round
trial to run. If Ray cannot prepare the complete transition, the run fails rather
than continuing a subset of targets.

The first implementation must test the actual ordering of Ray config mutation,
pause, checkpoint assignment, and resume. It may not claim transactionality
broader than Ray provides. The product invariant is that no supported path begins
a mixed generation.

### Planned completion

Completion is evaluated at a synchronized population boundary. Per-trial early
stopping that terminates one member independently is incompatible with an active
Clan. At the final boundary the scheduler verifies the complete decision, records
the final selected winner and its checkpoint as the Clan result, and stops the
complete population without starting an unnecessary generation.

Operational restart after external interruption is not silently inferred from
normal generation transitions. It is qualified separately when the support
milestone defines the persistent scheduler, exchange, and rendezvous envelope.

## Data and optimizer support boundaries

The architecture permits future support to grow without changing its owners, but
initial implementation must fail clearly outside the directly qualified path.
Likely first-path restrictions include:

- one process and one device per Tune trial;
- one dedicated single-node Ray cluster;
- DDP with Gloo for CPU qualification, followed by NCCL only after accelerator
  evidence;
- equal-length training partitions;
- one replicated validation workload;
- one optimizer with direct controlled-field application;
- no optimizer or learning-rate scheduler that competes with the controlled
  fields; and
- no SyncBatchNorm, forward buffer synchronization, elastic world-size change,
  FSDP, or model-sharded strategy.

These are qualification candidates, not permanent architecture. Each support
claim follows executable evidence.

## Public composition boundary

The advanced path exposes the concrete integration owners rather than a
package-owned Trainer or opaque experiment runtime:

- the Tune member adapter;
- the Tune scheduler;
- the round exchange;
- the cluster environment;
- the DDP strategy;
- the optimizer-configuration applier; and
- the round-boundary callback.

An advanced user supplies ordinary Lightning model, data, optimizer, and Trainer
construction through the member function's inputs. The eventual ordinary path may
manufacture the concrete Clan components and reserved configs, but it must use the
same lifecycle and leave the user's model and Trainer decisions with Lightning.

No public path requires a user-authored Ray `Trainable` subclass. Ray's internal
function-trainable machinery executes the member adapter, but that is an
implementation detail rather than the user programming model.

## Rejected alternatives

### Run the controller in the Tune scheduler

Rejected because it creates a second policy owner and abandons the accepted
process-local controller lifecycle.

### Report first, then invoke controller code inside stopped actors

Rejected as the primary design because it requires a private Tune actor-task seam
for ordinary policy execution. The round exchange lets each process execute its
own controller before reporting while preserving a narrow scheduler seam only for
checkpoint assignment.

### Continue a reporting function trial while waiting for the population

Rejected because the function would resume old-process Lightning work before the
complete transition is assigned. Every boundary report must pause its trial.

### Reuse trial actors across generations

Rejected for the initial path because FunctionTrainable reset semantics would
have to terminate and reconstruct the old training function while preserving no
stale Lightning runtime state. Replacement processes make the state authority
explicit: target config plus winner checkpoint.

### Use stock PBT as the Clan controller

Rejected because stock PBT owns quantile selection, donor choice, configuration
copy, and mutation. Those policies do not express one sole parent plus one
controller-produced target state for every member.

### Copy the winner's complete trial configuration

Rejected because it overwrites target member identity and target controller
state.

### Put controller state in the Lightning checkpoint

Rejected because winner-checkpoint cloning would copy the winner's controller
identity and random stream onto every target.

### Store controlled configuration beside controller state as another authority

Rejected because the current configuration is already part of the controller
state. A duplicate writable field could disagree with the state that produced it.

### Save every member checkpoint before selection

Rejected because every process-local controller already knows the selected
member before checkpointing. Only the unanimous winner's continuation state can
be used, so serializing losing trajectories adds I/O without adding correctness.

### Save only model parameters

Rejected because the method requires winner optimizer history and framework
training progress to continue the selected trajectory.

### Synchronize parameters or buffers after each update

Rejected because it erases the divergence on which member selection depends.
Only gradients are common during the round.

### Reduce fitness through DDP

Rejected because candidate-local fitness is the population comparison signal.

### Add a Clan checkpoint format or training loop

Rejected because Lightning already owns continuation-state serialization and the
training lifecycle.

## Behavioral-contract traceability

| Contract | Primary owners | Required evidence |
| --- | --- | --- |
| Common continuation state at round start | Ray assignment, member adapter, Lightning restore, Clan DDP strategy, optimizer applier | Direct restore-order contract plus multi-member observation before the first update. |
| One complete population produces one winner | `ClanController`, round exchange, Clan scheduler | Existing controller tests plus scheduler agreement and end-to-end transition tests. |
| Comparable member-local fitness | Lightning data configuration and round-boundary callback | Sampler/metric integration tests and end-to-end distinguishable candidates. |
| One clan-wide reduced gradient | PyTorch DDP through Clan DDP strategy | Gradient-before-step framework contract and real multi-rank test. |
| Controlled member divergence | Clan DDP strategy and member-local optimizers | Equal-input update test, buffer-broadcast test, and end-to-end divergence. |
| Winner continuation is sole parent | Round-boundary callback, Clan scheduler, member adapter, Lightning restore | Winner-only checkpoint contract, Ray assignment contract, and state observation after restore. |
| Target identity and control state survive | Clan scheduler, target Tune config, controller load, optimizer applier | Config-assignment, controller-RNG continuation, and optimizer-history preservation tests. |
| Partial population cannot transition | Controller guard, round exchange abort, Clan scheduler failure handling | Missing/duplicate/wrong-round tests and one real member-failure test. |
| Multi-round lifecycle repeats | All owners | Real two-or-more-round Ray/Lightning/DDP acceptance test. |
| Same authoritative inputs produce stable transition | `ClanController` state and ordered population conversion | Existing persistence tests extended through integration serialization. |

## Framework contracts required before implementation can be accepted

The design depends on version-specific behavior that must be proven directly:

1. Lightning recognizes the trial processes as externally launched DDP ranks and
   does not spawn children.
2. DDP initial synchronization occurs, gradients reduce across trials, parameters
   remain local after optimizer steps, and disabled buffer broadcast preserves
   persistent-buffer divergence.
3. A nonzero selected rank can produce a complete Lightning checkpoint through
   the strategy specialization while losing ranks do not write checkpoints.
4. The chosen Lightning hook applies controlled optimizer values after optimizer
   restoration and before the first update.
5. A Function API checkpoint can carry the Lightning checkpoint directory through
   Ray assignment and be materialized for `Trainer.fit(ckpt_path=...)` in the
   replacement member process.
6. Returning `PAUSE` for every boundary report prevents the reporting function
   trial from executing further work, and disabled actor reuse produces a
   replacement process on resume.
7. The scheduler can assign one reported winner checkpoint and distinct target
   controller states to every paused trial through Ray's native resume path.
8. Ray failure notification can abort the exchange and release or terminate
   blocked members.
9. The complete population reforms DDP and completes another round.

A probe used to establish one of these facts is temporary evidence. Only the
reduced framework-contract test that protects an accepted dependency belongs in
the product test suite.

## Design review questions

Human review should focus on these decisions before milestone decomposition:

1. Is the round exchange a justified narrow rendezvous owner, or is there a more
   native public Ray seam that lets process-local controllers consume one complete
   population without private actor invocation?
2. Is the Clan DDP strategy the correct single owner for external-rank setup,
   disabled buffer broadcast, and selected-rank checkpoint saving, or should the
   checkpoint specialization be separated without duplicating Lightning state
   assembly?
3. Is target-local controller state in the reserved Tune configuration the
   correct durable boundary, given that the winner Lightning checkpoint must not
   overwrite it?
4. Is the function member adapter a sufficiently narrow bridge between Ray's
   checkpoint/config lifecycle and one ordinary `Trainer.fit()` call?
5. Does the scheduler responsibility remain one coherent idea: pause, verify, and
   execute an already decided complete-population transition?

After these questions are accepted or corrected, the design can be decomposed
into stable implementation milestones and rolled out through contract-first TDD.
