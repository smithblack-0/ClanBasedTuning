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

- **PyTorch DDP** performs shared-gradient collectives and ordinary distributed
  model wrapping.
- **Lightning** performs training, validation, optimizer construction,
  checkpoint serialization, restoration, and data integration.
- **Ray Tune** owns trials, synchronous population scheduling, trial
  configuration, checkpoint assignment, pause, resume, scheduler persistence,
  and experiment restoration.
- **ClanBasedTuning** supplies only the behavior those frameworks do not natively
  express together: treating Tune trials as members of one DDP collective,
  selecting one parent for the next generation, reconciling a receiving
  member's optimizer configuration after inherited state is restored, and
  enforcing the collective constraints of the Clan mechanism.

This is a proposed framework architecture, not an endorsement of the current
proof-of-concept classes.

## Why the mechanism constrains the architecture

A Clan round begins from one inherited model and optimizer state. Members train
on distinct data, contribute to one reduced gradient, and apply that gradient
through different optimizer states and hyperparameters. They therefore share
training work while gradually diverging. Comparable fitness evaluation then
selects one member as the sole basis of the next generation.

Three consequences follow directly:

1. **Every member must be live for every training gradient.** Queuing or time
   multiplexing removes members from the shared work and changes the method.
2. **Member variation must remain optimizer-side.** Mutating model, data, or
   other gradient-defining configuration changes the meaning of the common
   gradient.
3. **Selection is a population lifecycle event.** Training, comparable
   evaluation, checkpoint availability, parent selection, restore, and
   optimizer reconciliation form one transition.

These are product constraints. Frameworks should continue to own the ordinary
mechanics that satisfy them.

## Native round lifecycle

A round should be the training interval between qualifying Lightning validation
and checkpoint reports.

Lightning already owns when validation occurs. A Clan-specific epoch counter,
batch conversion, optimizer-step clock, or timer would duplicate that authority
and create two definitions of the same boundary. Ray PBT can instead treat each
qualifying report as one population-decision opportunity; its report counter is
bookkeeping, not the definition of training progress.

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

Exact cadence, data-position continuation, and callback seams are Milestone 3
obligations rather than permanent project decisions.

## Evolution through Ray PBT

Ray's synchronous `PopulationBasedTraining` already owns the surrounding
population lifecycle: waiting for the population, ranking results, preparing a
source checkpoint before exploitation, assigning source checkpoints and
configuration to targets, pausing and resuming trials, and persisting scheduler
state with the Tune experiment.

ClanBasedTuning changes the selection policy. Instead of ordinary upper- and
lower-quantile exploitation, the Clan policy selects one deterministic winner,
preserves one elite configuration, and treats every other member as a target
for optimizer-only mutation.

The next implementation should therefore be a narrow PBT specialization. The
likely selection seam is version-sensitive, so Milestone 2 must protect it with
executable contract tests. A direct controller becomes appropriate only if
those tests show that the required policy cannot be expressed without
reproducing substantial Tune controller behavior.

## Checkpoint, restore, and optimizer authority

Ray and Lightning divide ordinary checkpoint responsibility cleanly:

- Lightning defines and serializes each member's training state.
- Ray PBT chooses the source and assigns its checkpoint to target trials.
- Lightning restores the assigned model and optimizer state.
- ClanBasedTuning applies only the receiving member's evolved optimizer values
  after restore.

Ray's Lightning callback can report a Lightning checkpoint with validation
metrics, and the FunctionTrainable path can return that reported checkpoint when
PBT requests the source save. This avoids a second Clan checkpoint scheduler.

Every divergent member must nevertheless be able to produce a trial-local
checkpoint. Lightning's ordinary DDP strategy writes only on global rank zero
because ordinary replicas are equivalent; Clan members are not. Milestone 3
must find and qualify the narrowest Lightning seam that permits every candidate
to supply a checkpoint through the native Ray reporting path.

Ray also provides native experiment restoration. `Tuner.restore` resumes
unfinished trials and can restore errored trials from their latest checkpoints.
That makes restoration a qualification problem, not a presumed need for a Clan
manifest or transaction system:

- Milestone 2 must prove that the specialized scheduler and synthetic trial
  population restore coherently, including a partially assembled synchronous
  boundary.
- Milestone 3 must prove the same path with real Lightning model, optimizer, and
  data state.
- Milestone 6 must qualify persistent storage, cluster failures, diagnostics,
  and restoration for the declared industry envelope.

Custom recovery machinery is justified only if those tests demonstrate a native
framework gap.

## Population and resource model

One Tune trial is one Clan member. Ray's population configuration should remain
the population authority rather than being mirrored by a second package count.

The first supported orchestration topology must keep that relationship
inspectable: generated trial count, concurrent capacity, Clan world size, and
dedicated resource allocation describe the same fully resident population.
The exact public admission check belongs to Milestone 3 manual composition and
Milestone 4 automated assembly.

The scheduler cannot guarantee residency alone because Ray may stage pending
actors through controller resource management. Admission therefore belongs at
the assembly boundary before any member enters DDP.

## Data and fitness

Training data retains normal distributed partitioning owned by Lightning and
PyTorch. Fitness data serves a different purpose: members are candidate models,
so they must be compared on the same examples under equivalent conditions.

The fitness value remains local to the Tune trial. A distributed metric
reduction would combine candidate scores and erase the population signal.
Standard PyTorch data primitives appear sufficient; Milestone 3 must define and
prove the concrete evaluation and reporting contract.

## DDP boundary

PyTorch DDP should own gradient bucketing, all-reduce, initial synchronization,
and the normal distributed wrapper lifecycle. ClanBasedTuning should not
reimplement collectives.

Focused probing supports this direction: DDP can synchronize an initial common
state, reduced gradients can remain common, and different optimizer
configurations can then produce divergent parameters. Runtime synchronization,
including buffer broadcast, must not erase that divergence.

Milestone 3 must commit the exact Lightning-facing contract tests and declare
support only for the precision, accumulation, model, and loader behavior those
tests qualify.

## Failure and completion

Every active member is part of one collective training entity. Failure of one
member therefore invalidates the active Clan. Planned completion has the same
population constraint: it occurs at a complete boundary and stops the complete
population.

Milestone 2 owns the controller-level decision and Ray lifecycle. Milestone 3
owns distributed termination behavior and diagnosis. Milestone 6 owns
production failure and recovery qualification. No milestone may silently fall
back to independent member recovery, a smaller DDP world, or mixed population
generations.

## Resulting proposed decisions

The research supports seven dated project decisions:

1. One Tune trial is one concurrently resident Clan member.
2. Lightning produces the qualifying evolutionary boundary.
3. Synchronous Ray PBT is the evolutionary lifecycle foundation.
4. Lightning owns checkpoint contents and restore; Ray owns source selection,
   assignment, scheduler persistence, and experiment restoration;
   ClanBasedTuning reconciles evolved optimizer values afterward.
5. Training data is partitioned, while fitness data is comparable and fitness
   remains member-local.
6. Native PyTorch DDP owns the shared-gradient substrate.
7. Failure and planned completion are collective.

The decisions are stated in
[project decisions](../decisions/project_decisions.md). Source-level support is
in the [evidence ledger](evidence_ledger.md). Completion obligations belong to
the [milestone gate files](../milestones/README.md), and later work is reviewed
through the [standing framework-native review](../reviews/framework_native_review.md).
