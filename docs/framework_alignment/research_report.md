# Framework-alignment research report

Status: explanatory research for Milestone 1 acceptance  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Conclusion

ClanBasedTuning should make the Clan mechanism native to the existing Ray Tune,
Lightning, and PyTorch execution model. It should not surround those frameworks
with a second scheduler, validation loop, checkpoint system, optimizer factory,
or distributed-training abstraction.

The proposed responsibility split is:

- **PyTorch DDP** performs the shared-gradient collectives and ordinary
  distributed model wrapping.
- **Lightning** performs training, validation, optimizer construction,
  checkpoint serialization, restoration, and data integration.
- **Ray Tune** owns trials, synchronous population scheduling, trial
  configuration, checkpoint assignment, pause, and resume.
- **ClanBasedTuning** supplies only the behavior those frameworks do not natively
  express together: treating Tune trials as members of one DDP collective,
  selecting one parent for the next generation, reconciling a receiving
  member's optimizer configuration after inherited state is restored, and
  enforcing the collective constraints of the Clan mechanism.

This is a proposed framework architecture, not an endorsement of the
proof-of-concept classes currently in the repository.

## Why the mechanism constrains the architecture

A Clan round begins from one inherited model and optimizer state. Members train
on distinct data, contribute to one reduced gradient, and apply that gradient
through different optimizer states and hyperparameters. They therefore share
training work while gradually diverging. Comparable fitness evaluation then
selects one member as the sole basis of the next generation.

Three consequences follow directly:

1. **Every member must be live for every training gradient.** Queuing or time
   multiplexing is not a slower form of the same method; it removes members from
   the shared work and changes the algorithm.
2. **Member variation must remain optimizer-side.** Mutating model, data, or
   other gradient-defining configuration would make the common gradient lose
   its intended meaning.
3. **Selection is a population lifecycle event.** Training, comparable
   evaluation, checkpoint availability, parent selection, restore, and
   optimizer reconciliation must form one coherent transition.

These are product constraints. The frameworks should continue to own the
ordinary mechanics that satisfy them.

## Native round lifecycle

A round should be the training interval between qualifying Lightning validation
and checkpoint reports.

Lightning already owns when validation occurs. A Clan-specific epoch counter,
batch conversion, optimizer-step clock, or timer would duplicate that authority
and create two definitions of the same boundary. Ray PBT can instead treat each
qualifying report as one population-decision opportunity; its report counter is
bookkeeping, not the definition of how much training belongs to the round.

The resulting lifecycle is:

1. Lightning trains according to the user's Trainer configuration.
2. Lightning enters a qualifying validation loop at a synchronized point.
3. Every member evaluates the same held-out examples and reports one local
   fitness value with one trial-local Lightning checkpoint.
4. Synchronous Ray PBT waits for the complete population.
5. ClanBasedTuning's evolutionary policy identifies one parent and target
   optimizer configurations.
6. Ray assigns the parent checkpoint and configurations to the next-generation
   trials.
7. Lightning restores the inherited model and optimizer state.
8. ClanBasedTuning reapplies each receiving member's optimizer configuration,
   and training resumes.

This research proposes that ownership split for Milestone 1 acceptance. Exact
subepoch cadence, checkpoint seams, and data-position continuation remain
integration questions that must be qualified later.

## Evolution through Ray PBT

Ray's synchronous `PopulationBasedTraining` already owns the population
lifecycle ClanBasedTuning needs: waiting for the population, ranking results,
checkpointing a source before exploitation, assigning source checkpoints and
configurations to targets, pausing, and resuming trials.

ClanBasedTuning changes the selection policy rather than that lifecycle. Instead
of ordinary upper- and lower-quantile exploitation, the Clan policy selects one
deterministic winner, preserves an elite configuration, and treats every other
member as a target for optimizer-only mutation.

The recommended next implementation is therefore a narrow PBT specialization.
The relevant Ray seam is version-sensitive and must be protected by executable
contract tests in the controller milestone. Reimplementing the complete
scheduler would use more internal Tune behavior and duplicate more framework
responsibility.

## Checkpoint and optimizer authority

Ray and Lightning divide checkpoint responsibility cleanly:

- Lightning defines and serializes each member's training state.
- Ray PBT chooses which checkpoint becomes the source and assigns it to target
  trials.

Ray's Lightning callback can report a Lightning checkpoint with validation
metrics, and the FunctionTrainable path can return that reported checkpoint when
PBT later requests the source save. This avoids a second Clan checkpoint
scheduler.

The integration must still allow every divergent member to produce a
trial-local checkpoint. Lightning's ordinary DDP strategy writes only on global
rank zero because ordinary DDP replicas are equivalent. Clan members are not.
The narrow member-local save seam belongs to later Lightning integration work.

After restore, the parent optimizer state must remain intact while the receiving
trial adopts its own next-generation optimizer configuration. Lightning should
restore the optimizer normally; ClanBasedTuning should then reconcile only the
explicitly evolved optimizer values. An independent learning-rate scheduler
would compete for authority over those values and is not part of the initial
support model.

Whole-experiment recovery is different from ordinary winner transfer. Tune may
persist experiment metadata while a synchronous population boundary is only
partially reported. Restoring that snapshot cannot yet be assumed to recreate a
coherent Clan generation. The initial architecture therefore supports normal
PBT checkpoint inheritance but defers interrupted-round experiment recovery.

## Population and resource model

One Tune trial is one Clan member. Ray's population configuration should be the
single population authority rather than being mirrored by a second
ClanBasedTuning count.

The initial topology should keep that relationship inspectable: the generated
trial count, concurrent trial capacity, Clan world size, and dedicated device
allocation must describe the same fully resident population. More elaborate
search-space expansion or partial admission can be considered later only if it
preserves that invariant without adding a second source of truth.

The primary admission check cannot live solely inside the scheduler. Ray may
stage pending actors through controller behavior outside the scheduler's choice
of the next runnable trial. The eventual assembly path must therefore validate
full residency before any member enters the DDP collective.

## Data and fitness

Training data should retain the normal distributed partitioning owned by
Lightning and PyTorch. Fitness data serves a different purpose: the members are
candidate models, so they must be compared on the same examples under the same
deterministic conditions.

The fitness value must remain local to the Tune trial. A distributed metric
reduction would combine the candidate scores and erase the signal the
population controller needs. Standard PyTorch data primitives appear sufficient
to express replicated evaluation; the exact public helper and validation
contract belong to later integration design.

## DDP boundary

PyTorch DDP should continue to own gradient bucketing, all-reduce, and the
normal distributed wrapper lifecycle. ClanBasedTuning should not reimplement
collectives.

Focused probing supports a native-DDP direction: DDP can synchronize an initial
common state, reduced gradients can remain common, and different optimizer
configurations can then produce divergent parameters. Runtime buffer
broadcasting must not erase that divergence. The exact Lightning hook and the
supported precision, accumulation, and model behaviors require direct contract
tests before they become support claims.

## Failure and completion

Every active member is part of one collective training entity. Failure of one
member therefore invalidates the active Clan. Initial behavior should stop or
fail the complete population rather than recover one trial independently or
continue with a smaller world.

Planned completion has the same collective constraint. Tune's ordinary
per-trial stopping can terminate one member before the synchronous population
decision is complete, and Lightning early stopping can do the same. A planned
end must be decided at a synchronized population boundary and stop the complete
Clan. The evolutionary-controller milestone must choose the narrowest native
owner for that decision.

External cancellation or a hard global interruption may stop the complete job
without another population transition. That is an operational interruption,
not member-local completion.

## Resulting project direction

The research supports nine proposed decisions and boundaries:

1. One Tune trial is one concurrently resident Clan member.
2. Lightning owns the qualifying evaluation cadence.
3. Synchronous Ray PBT is the evolutionary lifecycle foundation.
4. One deterministic parent supplies the next generation.
5. Lightning owns checkpoint contents and restore; Ray owns source selection and
   transfer; ClanBasedTuning reconciles evolved optimizer values afterward.
6. Training data is partitioned, while fitness data is replicated and fitness
   remains member-local.
7. Native PyTorch DDP owns the shared-gradient substrate.
8. Failure and planned completion are collective; interrupted-round experiment
   recovery is deferred.
9. Current proof-of-concept code is evidence, not architectural authority.

The precise decisions and remaining open questions are recorded in the
[decision register](decision_register.md). Source-level support is in the
[evidence ledger](evidence_ledger.md). Later designs are judged through the
[framework-native engineering review](framework_native_review.md).
