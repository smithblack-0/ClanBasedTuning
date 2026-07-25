# Framework-alignment research report

Status: explanatory research for Milestone 1 acceptance  
Date: 2026-07-24  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Conclusion

ClanBasedTuning should express the Clan mechanism through the existing PyTorch,
Lightning, and Ray Tune responsibility model. It should not surround those
frameworks with a second training loop, validation clock, checkpoint system,
optimizer factory, trial runtime, or gradient-communication implementation.

The proposed responsibility model is:

- **PyTorch distributed strategies** perform ordinary model wrapping, initial
  synchronization, gradient bucketing, and shared-gradient collectives.
- **Lightning** performs training, validation, optimizer construction,
  checkpoint serialization and restoration, and data integration.
- **Ray Tune** owns trial identity and execution, resource scheduling, trial
  configuration, checkpoint/configuration assignment, pause and resume, and
  experiment persistence in the Ray-backed path.
- **ClanBasedTuning** supplies the behavior those frameworks do not express
  together: one live Tune trial per Clan member, one complete-population
  evolutionary decision, sole-parent inheritance, optimizer-only variation,
  post-restore optimizer reconciliation, and collective Clan validity.

This model is proposed for Milestone 1 acceptance. It does not certify the
current proof-of-concept classes, and it does not yet choose the implementation
form of the Milestone 2 controller.

## What the Clan mechanism requires

A Clan round begins from one inherited model and optimizer state. Members train
on distinct data, contribute to one reduced gradient, and apply that gradient
through different optimizer states and hyperparameters. Comparable fitness
evaluation then selects one member whose state becomes the sole basis of the
next generation.

The mechanism creates four architectural constraints:

1. **The complete active population participates in shared training.** Queuing,
   time-multiplexing, or silently dropping members changes the work being shared.
2. **Variation remains optimizer-side during a round.** Mutating model, data, or
   another gradient-defining choice changes the meaning of the common gradient.
3. **Fitness remains candidate-local until population comparison.** Reducing
   candidate scores across members destroys the signal used for selection.
4. **A round transition has one policy owner and native execution owners.** The
   controller decides the parent and next optimizer configurations; framework
   machinery executes checkpoint assignment, restoration, and resumed training.

These are project constraints. They do not imply that ClanBasedTuning must own
the ordinary mechanics used to satisfy them.

## Native round lifecycle

Lightning already owns the training and validation cadence. Defining a second
Clan epoch, batch, optimizer-step, or wall-clock clock would create two
potentially inconsistent descriptions of the same progress boundary.

The intended Ray/Lightning lifecycle is therefore:

1. Lightning trains according to the user's Trainer configuration.
2. Lightning enters a qualifying validation-and-checkpoint event.
3. Every live member evaluates the same held-out workload and reports one
   member-local fitness value with one trial-local checkpoint.
4. The population decision receives one complete population result.
5. ClanBasedTuning selects the sole parent and produces the next member optimizer
   configurations.
6. Ray Tune assigns the selected checkpoint and target configuration through its
   native trial lifecycle.
7. Lightning restores the inherited model, optimizer, and training progress.
8. ClanBasedTuning reapplies the receiving member's evolved optimizer values.
9. The next live population reforms its distributed execution and continues.

Exact cadence, supported loader and accumulation behavior, checkpoint hooks,
resource admission, and process-group reformation are integration design work.
They become enforceable when Milestone 3 builds the complete manual workflow.

## Evolutionary controller form remains a Milestone 2 choice

Ray's synchronous `PopulationBasedTraining` provides a relevant policy/executor
split. Its scheduler receives trial results and decides exploit/explore actions,
while Tune's runtime performs checkpoint preparation, assignment, pause, resume,
and trial execution. A narrow PBT specialization may therefore express the Clan
population decision without rebuilding the surrounding lifecycle.

That is a leading candidate, not yet a durable project decision. The likely
selection seam in Ray 2.56 is version-sensitive and may be too entangled with
ordinary PBT ranking or mutation policy. Milestone 2 must compare two designs
against direct source and executable seam evidence:

- **Narrow PBT specialization:** replace only the population decision while
  retaining native scheduler/executor behavior.
- **Independent controller with a thin Ray adapter:** keep the public policy
  independent and translate its decision into the narrowest Tune scheduling
  surface available.

The choice must preserve independent controller invocation, avoid a second Tune
lifecycle, retain one policy authority, and expose only the framework state that
is genuinely required. A direct controller is not justified merely because a
private seam is inconvenient; a PBT subclass is not justified merely because it
already exists.

## State-transition authority

The controller decides **which member is the parent**. Ray does not own that
Clan policy. In the Ray-backed integration, Ray owns execution of the resulting
checkpoint and configuration assignment.

Lightning owns the contents of each trial checkpoint and restoration of model,
optimizer, and training progress. ClanBasedTuning then applies the receiving
member's evolved optimizer values after inherited optimizer state is loaded.
This order preserves the parent's moments, momentum, counters, and other
optimizer history while allowing the next generation to use different optimizer
hyperparameters.

Every divergent trial must be able to produce a trial-local checkpoint because
any member may be selected. Lightning's ordinary DDP checkpoint assumptions may
require a narrow integration seam when different Tune trials participate in one
collective. That seam is an integration responsibility, not a reason to create a
Clan checkpoint scheduler.

Ray also provides experiment restoration. That evidence establishes a design
rule: test native restoration before inventing Clan-specific recovery state. It
does not make interruption recovery part of the controller milestone. Normal
checkpoint-driven next-generation continuation is qualified with the complete
Milestone 3 workflow; production interruption recovery is qualified when the
industry milestone defines its support envelope.

## Population and resources

In the Ray-backed program, one Tune trial is one Clan member. Ray's generated
trial set remains the population authority; ClanBasedTuning should not mirror it
with an independent count that can disagree.

The complete population must be concurrently resident whenever shared gradients
are computed. Scheduler policy alone cannot guarantee that condition because
Ray's controller also stages actors through resource management. Population
admission must therefore be checked at the orchestration boundary before any
member enters the distributed collective. Manual integration first proves the
contract; the usability milestone later automates it.

## Data and fitness

Training data retains normal distributed partitioning owned by Lightning and
PyTorch. Fitness data has a different purpose: it compares divergent candidate
models, so every member must evaluate the same held-out workload under equivalent
conditions.

Each fitness value remains member-local until population comparison. A DDP metric
reduction would combine candidate scores and erase the population signal.
Standard PyTorch and Lightning data mechanisms appear sufficient; the complete
integration must define and prove the supported sampler, transform, ordering,
loader-length, boundary, and reporting contract.

## Shared-gradient execution

PyTorch's native distributed strategies should own ordinary shared-gradient
execution. For the first complete integration, DDP is the relevant substrate:
it can synchronize an initial common state and reduce gradients while local
optimizer states and hyperparameters subsequently produce divergent parameters.
Runtime synchronization, including buffer behavior, must not erase that intended
divergence.

Later industry support may add FSDP or another Lightning-native model-sharding
strategy. Those modes must preserve the same Clan semantics through their native
lifecycle. The project should not encode “one DDP process equals one member” as a
permanent architecture if doing so would preclude the roadmap's model-sharding
milestone.

## Failure and completion

An active Clan is one complete population participating in a shared-gradient
workflow. Loss of a required member invalidates that active Clan; continuing with
a smaller population would change both the distributed world and the scientific
method.

Planned completion likewise applies to the complete Clan and occurs at a
coherent population boundary. The controller must not manufacture a valid
population decision from incomplete input. The integration must terminate or
invalidate broken distributed execution clearly. The industry milestone later
qualifies operational diagnosis and recovery for its declared support envelope.

These are cumulative requirements, not three different controller,
integration, and production “recovery” subsystems.

## Resulting proposed decisions

The research supports six proposed cross-milestone decisions:

1. One Ray Tune trial represents one concurrently live Clan member.
2. Lightning produces the qualifying round boundary.
3. ClanBasedTuning decides the sole-parent population transition; native
   frameworks execute trial state assignment and restoration.
4. Training data is partitioned, while fitness data is comparable and remains
   member-local.
5. Native PyTorch distributed strategies own shared-gradient execution.
6. Active-population validity and planned completion are collective.

The Milestone 2 controller implementation form remains intentionally open until
its first work unit qualifies the available framework seams.

The proposed decisions are stated in
[project decisions](../decisions/project_decisions.md). Source and probe support
is preserved in the [evidence ledger](evidence_ledger.md). Completion obligations
belong to the [milestone gate system](../milestones/README.md), and implementation
boundaries are reviewed through the
[standing framework-native review](../reviews/framework_native_review.md).
