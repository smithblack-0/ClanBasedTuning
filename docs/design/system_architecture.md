# ClanBasedTuning system architecture

Status: proposed design under human review  
Date: 2026-07-31  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Design result

ClanBasedTuning composes one Tune trial per Clan member into one externally
launched Lightning DDP job. PyTorch DDP supplies one reduced gradient to every
member. Each member applies that gradient through its own optimizer history and
controlled hyperparameters. At a qualifying Lightning validation boundary, each
process publishes its local result, receives the same complete population,
advances its existing `ClanController`, and reports one transition proposal and
one trial-local Lightning checkpoint to Tune. A narrow Tune scheduler verifies
that the proposals agree and assigns the winning checkpoint plus each target's
own controller state and next configuration through Ray's native trial
lifecycle.

The next generation starts in new or resumed trial processes. Lightning restores
the winner's continuation state. ClanBasedTuning then reapplies the receiving
member's controlled optimizer values without replacing inherited optimizer
history. The population reforms DDP and continues.

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
8. Ray executes checkpoint and target-configuration assignment; it does not
   select the winner or mutate optimizer values.
9. The winner supplies continuation state. The receiver supplies member identity,
   controller state, and next controlled optimizer configuration.
10. A partial or corrupt population cannot select, inherit, resume, or continue.

## State ownership

| State | Authoritative owner | Transition behavior |
| --- | --- | --- |
| Model parameters and persistent buffers | Lightning checkpoint produced from one member's live model | Copied from the selected winner to every next-generation member. |
| Optimizer tensors, counters, moments, and momentum | Lightning checkpoint produced from the selected winner | Restored from the winner before receiving controlled values are reapplied. |
| Lightning loop and training-progress state | Lightning checkpoint | Restored from the winner to every receiver. |
| Controlled optimizer values for the current round | Receiving member's `ClanController` state | Remain target-local and are applied after optimizer restoration. |
| Member identity | Ray trial configuration in the reserved Clan namespace | Never copied from the winner. |
| Controller random stream and next-round state | Receiving member's post-decision controller state | Remain target-local and travel in the target trial configuration, not the winner checkpoint. |
| Complete round population | Round exchange, derived from one report per configured member | Exists only long enough for every local controller to consume the same immutable population. |
| Winner and next configurations | Each local `ClanController`; agreement verified by the scheduler | The scheduler executes the agreed result but does not recompute it. |
| Trial actor, process group, device assignment, pause, and resume | Ray Tune and Lightning/PyTorch | Recreated or resumed by the frameworks; never serialized as Clan state. |

The split between the winner checkpoint and target trial configuration is
fundamental. Copying the winner's complete trial configuration or controller state
would collapse member identity and mutation streams. Storing target-local control
state inside the Lightning checkpoint would make Ray's winner-checkpoint
assignment overwrite every receiver with the winner's controller state.

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
- the receiving member's next controlled configuration;
- the receiving member's post-decision controller state; and
- the trial-local Lightning checkpoint registered with the report.

The report contains the target's control continuation and the candidate's
training checkpoint as separate fields. The scheduler uses the checkpoint only
when that reporting member is the agreed winner. It uses each report's controller
state and next configuration only for that report's target member.

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

**Main idea:** rendezvous one result from every configured member and return the
same immutable population to every member.

The proposed implementation is a small asynchronous Ray actor created once per
Clan run. Each member calls one operation equivalent to
`publish_and_wait(round_result)`. The actor:

- accepts exactly one result per member for the active round;
- verifies Clan identity, member identity, and round identity;
- orders the completed population by stable member identity;
- releases all waiting members with the same population snapshot;
- retains no policy, checkpoint, model, optimizer, or mutation behavior; and
- can be aborted by the Tune-side lifecycle owner when a member fails.

An asynchronous actor is required so one blocked publication does not prevent
later members from submitting. The actor is transport and rendezvous, not a
second population authority: expected membership is derived from the same Tune
trial construction that defines the live Clan.

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
independently checkpointed Clan member.

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
4. It permits every rank to write a Lightning checkpoint to its own trial-local
   path at the round boundary. Lightning's ordinary DDP strategy writes only on
   global rank zero because ranks normally represent replicas of one model;
   Clan ranks are divergent candidates and any one may win.

The per-rank checkpoint change remains inside the Lightning strategy and
`CheckpointIO` lifecycle. It does not introduce a Clan checkpoint format or call
`torch.save` on an independently assembled state dictionary.

The strategy does not synchronize optimizer history or parameters after optimizer
updates. It relies on native DDP gradient reduction and explicitly tests that the
framework configuration preserves divergence.

### Round-boundary callback

**Main idea:** close one local Lightning round and emit one complete transition
report.

At the accepted validation boundary, the callback performs this sequence:

1. Ignore Lightning sanity checking and any validation event not configured as a
   Clan boundary.
2. Read the configured fitness metric from the member's local Lightning metrics
   without distributed metric reduction.
3. Enter a DDP barrier so every member has completed equivalent validation work.
4. Call `controller.set_fitness()`, causing the local result to be published to
   the round exchange.
5. Wait for the same complete population and call `controller.advance()`.
6. Capture the local winner, next configuration, and post-decision controller
   state.
7. Ask Lightning to save a checkpoint to the member's trial-local checkpoint
   directory.
8. Report the transition metadata and checkpoint through Tune's reporting API.

The callback does not train, validate, select the winner, mutate values, assign a
checkpoint to another trial, or apply the next configuration to the current
optimizer. The reported process is at the end of the old round. Ray will pause
and transition it; the next process applies the target configuration only after
restoring the selected checkpoint.

The callback must not serialize its controller or member-local control state into
Lightning callback state. Its Lightning checkpoint contribution is empty unless
a later accepted design identifies genuinely winner-owned callback state.

### Clan Tune scheduler

**Main idea:** verify and execute one complete, unanimous Clan transition through
Ray's native trial lifecycle.

The scheduler receives one transition report from every trial and holds each
trial at the boundary. When the population is complete, it verifies:

- exactly one report per configured member;
- one completed round identity;
- one next round identity;
- one agreed winner;
- stable target member identities;
- one target-local controller state and next configuration per member; and
- an assignable checkpoint from the agreed winner.

It then:

1. selects the already reported checkpoint belonging to the agreed winner;
2. preserves every target trial's user configuration and stable member identity;
3. replaces only the reserved Clan control namespace with that target's next
   round, controller state, and controlled configuration;
4. assigns the winner checkpoint as every target's next continuation checkpoint;
5. lets Ray pause, stop, restore, and resume the target trials; and
6. clears the completed transition only after every assignment is prepared.

The scheduler does not compare fitness, invoke mutation, construct controller
state, save Lightning checkpoints, or manage a process group.

Ray 2.56 does not expose the complete cross-trial checkpoint reassignment as a
stable high-level public method. The implementation may therefore require the
same narrow version-sensitive controller and checkpoint-manager seam used by
Ray's PBT scheduler. That seam must remain isolated in this class, covered by a
direct Ray framework-contract test, and pinned to the qualified Ray version. It
must not leak into controller, Lightning, or user APIs.

Standard `PopulationBasedTraining` is not itself the policy implementation for
this design. Its quantile selection, donor choice, target-config copying, and
mutation behavior conflict with sole-parent Clan policy and target identity. The
Clan scheduler may reuse Ray lifecycle mechanisms demonstrated by PBT, but not its
population policy.

### Optimizer-configuration applier

**Main idea:** apply the receiving member's declared controlled values to already
constructed and restored optimizer objects.

The lifecycle position is fixed even though the complete Milestone 5 rule system
is not:

1. Lightning constructs the user's optimizer objects.
2. Lightning restores the winner's optimizer history from the assigned
   checkpoint.
3. On the first training-start hook after restoration, ClanBasedTuning applies
   the receiving member's controlled values.
4. Training begins only after application succeeds.

The applier must not construct optimizers, replace optimizer state dictionaries,
or interpret the user's full Tune configuration as an optimizer schema. The
initial manual workflow may qualify one explicit optimizer and direct field
mapping. The later optimizer-utility design can generalize targeting and
remapping without changing this lifecycle boundary.

The selected Lightning hook must be proven by a framework-contract test to occur
after optimizer restoration and before the first optimizer update. A hook that
runs before `restore_training_state()` is invalid because the restored checkpoint
would overwrite the receiving values.

## Reserved Tune configuration namespace

ClanBasedTuning requires a package-owned nested namespace inside each Tune trial
configuration. The exact key is an implementation detail, but its contents and
update rule are architectural:

- stable Clan or experiment identity;
- stable member identity;
- population size;
- current round identity;
- round-exchange reference or name;
- DDP rendezvous specification;
- target-local controller state; and
- target-local controlled optimizer configuration.

User experiment configuration remains outside this namespace. A generation
transition updates only the target's reserved Clan values. It never copies the
winner's complete Tune config onto another member.

The user-facing model or workload builder should receive the user's configuration
without package control metadata unless the user explicitly requests access to
it.

## Complete lifecycle

### 1. Driver construction and admission

The Tune driver creates exactly one trial configuration per member identity and
one round exchange for the Clan. It configures the custom scheduler and requires
`max_concurrent_trials` equal to the population size.

Before starting, the manual workflow verifies that the dedicated Ray environment
has sufficient resources for the entire population. The implementation must not
rely on PBT-style time multiplexing because a queued member would be absent from
DDP gradient reduction.

Atomic reservation across independent Tune trials is not claimed by this initial
architecture. The first supported path therefore requires a dedicated or
otherwise reserved resource envelope and fails preflight when declared resources
are insufficient.

### 2. Member process construction

Each trial process reads its stable identity and target-local control state from
the reserved config. It constructs:

- its local `ClanController`;
- callbacks adapting controller publication and loading to the round exchange;
- the external cluster environment;
- the Clan DDP strategy;
- the round-boundary callback; and
- the optimizer-configuration applier.

The user's ordinary Lightning module, dataloaders, optimizer construction, and
Trainer choices remain user- and Lightning-owned. No public API requires the user
to subclass Ray `Trainable` or implement `step`, `save_checkpoint`,
`load_checkpoint`, or `reset_config` methods.

A Tune function entrypoint or equivalent package adapter may host the composition,
but it calls one ordinary `Trainer.fit()` and contains no training loop of its
own.

### 3. Initial state

For a fresh run, native DDP initialization synchronizes model parameters and
persistent buffers. Every optimizer begins from the same empty or explicitly
provided history, after which each member's initial controlled configuration is
applied.

For a seeded or resumed run, every member receives the same initial Lightning
checkpoint through Ray. Lightning restores the common continuation state before
target-local controlled values are applied.

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
the exchange and receives the same ordered population. Every process-local
controller advances from that population.

The controllers are expected to produce one winner and one target-local next
configuration per member. Scheduler-side agreement checking is a corruption and
consistency guard, not a second policy vote.

### 7. Candidate checkpoint and Tune report

Every member saves its own divergent Lightning continuation state to a unique
trial-local path. Every member reports its local checkpoint, fitness, selected
winner, and target-local next control state to Tune.

Saving every candidate is necessary at this boundary because the selected winner
is not known to Ray's transition executor until it has all reports. Later evidence
may justify an optimized winner-only save, but that optimization must not require
duplicating Lightning checkpoint serialization or moving policy into the
scheduler.

### 8. Sole-parent transition

The Clan scheduler waits for the complete report population, verifies unanimous
policy output, and chooses the checkpoint already reported by the winner. It
assigns that checkpoint to every target while preserving each target's identity
and installing its own post-decision controller state and next configuration.

A failure before all assignments are prepared leaves the old round authoritative;
the scheduler must not publish a partially advanced generation.

### 9. Restore and reconcile

Ray restarts or resumes every target from the assigned winner checkpoint.
Lightning restores model state, optimizer history, and training progress. The
optimizer applier then writes the target's controlled values into the restored
optimizer without reconstructing it or clearing history.

Controller state is loaded from the target Tune configuration, not from the
winner checkpoint.

### 10. Reformation and continuation

The complete target population reforms the DDP world, verifies common
continuation state, and begins the next round. The same lifecycle repeats until a
synchronized population boundary satisfies the configured completion rule.

## Failure and completion

### Member failure before the boundary

Ray reports the failed trial to the Clan scheduler. The scheduler marks the
active round invalid, aborts the round exchange so waiting members are released,
and stops or invalidates every remaining member. No partial population decision
or next-generation assignment is allowed.

### Corrupt or disagreeing reports

Duplicate member IDs, wrong rounds, missing checkpoints, inconsistent winners,
or malformed target state fail before checkpoint assignment. The previous round
remains the last complete authoritative generation.

### Failure during assignment

The scheduler prepares all target assignments before allowing any next-round
training. If Ray cannot prepare the complete transition, the run fails rather
than continuing a subset of targets.

The first implementation must test the actual ordering of Ray mutation, pause,
checkpoint assignment, and resume. It may not claim transactionality broader than
Ray provides. The product invariant is that no supported path begins a mixed
generation.

### Planned completion

Completion is evaluated at a synchronized population boundary. Per-trial early
stopping that terminates one member independently is incompatible with an active
Clan. The scheduler ends the complete population together after the last accepted
round.

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

- the Tune scheduler;
- the round exchange;
- the cluster environment;
- the DDP strategy;
- the round-boundary callback; and
- the optimizer-configuration applier.

An advanced user supplies an ordinary Lightning module, Trainer construction,
training and validation data, and Ray run resources. The eventual ordinary path
may manufacture these concrete components and reserved configs, but it must use
the same lifecycle and leave the user's model and Trainer decisions with
Lightning.

No public path requires a user-authored Ray `Trainable` subclass. Ray's internal
function-trainable machinery may execute the member function, but that is an
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

### Use stock PBT as the Clan controller

Rejected because stock PBT owns quantile selection, donor choice, configuration
copy, and mutation. Those policies do not express one sole parent plus one
controller-produced target configuration for every member.

### Copy the winner's complete trial configuration

Rejected because it overwrites target member identity, target controller state,
and target-specific next configuration.

### Put controller state in the Lightning checkpoint

Rejected because winner-checkpoint cloning would copy the winner's controller
identity and random stream onto every target.

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
| Common continuation state at round start | Ray assignment, Lightning restore, Clan DDP strategy, optimizer applier | Direct restore-order contract plus multi-member observation before the first update. |
| One complete population produces one winner | `ClanController`, round exchange, Clan scheduler | Existing controller tests plus scheduler agreement and end-to-end transition tests. |
| Comparable member-local fitness | Lightning data configuration and round-boundary callback | Sampler/metric integration tests and end-to-end distinguishable candidates. |
| One clan-wide reduced gradient | PyTorch DDP through Clan DDP strategy | Gradient-before-step framework contract and real multi-rank test. |
| Controlled member divergence | Clan DDP strategy and member-local optimizers | Equal-input update test, buffer-broadcast test, and end-to-end divergence. |
| Winner continuation is sole parent | Clan scheduler and Lightning restore | Ray checkpoint-assignment contract and state-partition observation after restore. |
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
3. Every rank can produce a complete Lightning checkpoint through the strategy
   specialization.
4. The chosen Lightning hook applies controlled optimizer values after optimizer
   restoration and before the first update.
5. Tune reports and pauses every member at one boundary without advancing an old
   actor into the next round.
6. The scheduler can assign one reported winner checkpoint and distinct target
   configs to every trial through Ray's native resume path.
7. Ray failure notification can abort the exchange and release blocked members.
8. The complete population reforms DDP and completes another round.

A probe used to establish one of these facts is temporary evidence. Only the
reduced framework-contract test that protects an accepted dependency belongs in
the product test suite.

## Design review questions

Human review should focus on these decisions before milestone decomposition:

1. Is the round exchange a justified narrow rendezvous owner, or is there a more
   native public Ray seam that lets process-local controllers consume one complete
   population without private actor invocation?
2. Is the Clan DDP strategy the correct single owner for external-rank setup,
   disabled buffer broadcast, and per-rank checkpoint saving, or should the
   checkpoint specialization be separated without duplicating Lightning state
   assembly?
3. Is target-local controller state in the reserved Tune configuration the
   correct durable boundary, given that the winner Lightning checkpoint must not
   overwrite it?
4. Is saving every candidate checkpoint an acceptable first correct design before
   considering a winner-only optimization?
5. Does the scheduler responsibility remain one coherent idea: verify and execute
   an already decided complete-population transition?

After these questions are accepted or corrected, the design can be decomposed
into stable implementation milestones and rolled out through contract-first TDD.
