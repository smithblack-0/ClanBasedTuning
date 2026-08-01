# Framework-alignment research report

Status: accepted explanatory basis with 2026-07-25 boundary correction  
Date: 2026-07-25  
Version scope: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## Conclusion

ClanBasedTuning should express the Clan mechanism through the existing PyTorch,
Lightning, and Ray Tune responsibility model. It should not surround those
frameworks with a second training loop, validation clock, checkpoint system,
optimizer factory, trial runtime, or gradient-communication implementation.

The accepted responsibility baseline is:

- **PyTorch distributed execution** performs ordinary model wrapping, initial
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

The framework-independent population policy and its Ray invocation path are
separate engineering products. Milestone 2 establishes the policy contract from
ordinary data. Milestone 3 chooses and qualifies the Ray-native seam that gathers
that data and executes the decision.

This separation prevents version-sensitive scheduler and trial constraints from
becoming controller design requirements before the controller's own lifecycle,
data model, algorithms, and state are accepted.

## What the Clan mechanism requires

A Clan round begins from one inherited model and optimizer state. Members train
on distinct data, contribute to one reduced gradient, and apply that gradient
through different optimizer states and hyperparameters. Comparable fitness
evaluation then selects one member whose state becomes the sole basis of the
next generation.

The mechanism creates four architectural constraints:

1. **The complete active population participates in shared training.** Queuing,
   time-multiplexing, or silently dropping members changes the shared work.
2. **Variation remains optimizer-side during a round.** Mutating model, data, or
   another gradient-defining choice changes the meaning of the common gradient.
3. **Fitness remains candidate-local until population comparison.** Reducing
   candidate scores across members destroys the selection signal.
4. **A round transition has one policy owner and native execution owners.** The
   controller decides the parent and next optimizer configurations; framework
   machinery executes checkpoint assignment, restoration, and resumed training.

These constraints do not imply that ClanBasedTuning owns the ordinary mechanics
used to satisfy them.

## Native round lifecycle

Lightning already owns the training and validation cadence. Defining a second
Clan epoch, batch, optimizer-step, or wall-clock clock would create two
potentially inconsistent descriptions of the same progress boundary.

The intended Ray/Lightning lifecycle is:

1. Lightning trains according to the user's Trainer configuration.
2. Lightning enters a qualifying validation-and-checkpoint event.
3. Every live member evaluates the same held-out workload and reports one
   member-local fitness value with one trial-local checkpoint.
4. The Ray integration gathers the ordinary population data required by the
   accepted controller.
5. ClanBasedTuning selects the sole parent and produces the next member optimizer
   configurations.
6. Ray Tune assigns the selected checkpoint and target configuration through its
   native trial lifecycle.
7. Lightning restores the inherited model, optimizer, and training progress.
8. ClanBasedTuning reapplies the receiving member's evolved optimizer values.
9. The next live population reforms distributed execution and continues.

Exact cadence, supported loader and accumulation behavior, checkpoint hooks,
resource admission, process-group reformation, and the Ray controller invocation
seam are integration design work. They become enforceable when Milestone 3 builds
the complete manual workflow.

## Independent controller before Ray integration

The Clan population policy can be defined without a framework runtime. It needs
one complete population result with associated member identities, fitness values,
and optimizer-hyperparameter configurations. It returns the selected member and
the next configuration for each member.

Milestone 2 therefore establishes:

- the controller lifecycle and non-ownership boundary;
- the accepted input and output data structures;
- selection, mutation, bounds, randomness, and failure algorithms;
- intentional state, if any;
- focused and plain-data compatibility tests; and
- a repeated synthetic loop demonstrating how an external training system would
  supply fitness and consume the decision.

Ray's synchronous `PopulationBasedTraining` remains relevant evidence for the
later execution seam. Its scheduler receives trial results and decides
exploit/explore actions while Tune performs checkpoint preparation, assignment,
pause, resume, resources, and trial execution. A narrow specialization may be the
best Milestone 3 seam, or a thin adapter around the independent controller may be
cleaner.

That choice requires direct Ray evidence after the controller contract is stable.
Neither conclusion follows automatically:

- a private seam is not rejected merely because it is private;
- an existing PBT class is not selected merely because it already provides
  nearby lifecycle behavior; and
- an adapter is not preferred merely because it appears framework-neutral.

The selected Milestone 3 design must preserve one policy authority, native Tune
lifecycle ownership, the smallest justified version-sensitive surface, and
auditable translation between framework state and controller data.

## State-transition authority

ClanBasedTuning decides **which member is the parent**. That is the defining Clan
population policy. Ray does not own that decision.

In the Ray-backed integration, Ray owns execution of the resulting checkpoint
and configuration assignment. Lightning owns checkpoint contents and restoration
of model, optimizer, and training progress. ClanBasedTuning then applies the
receiving member's evolved optimizer values after inherited optimizer state is
loaded.

This ordering preserves the parent's moments, momentum, counters, and other
optimizer history while allowing the next generation to use different optimizer
hyperparameters.

Every divergent trial must be able to produce a trial-local checkpoint because
any member may be selected. Lightning's ordinary DDP checkpoint assumptions may
require a narrow integration seam when different Tune trials participate in one
collective. That seam is an integration responsibility, not a reason to create a
Clan checkpoint scheduler.

Ray also provides experiment restoration. This establishes a design rule: test
native restoration before inventing Clan-specific recovery state. It does not
make interruption recovery part of the controller milestone. Normal
checkpoint-driven next-generation continuation is qualified with the complete
Milestone 3 workflow. Operational interruption recovery is qualified when the
industry milestone defines its support envelope.

## Population and resources

One Tune trial is one Clan member in the Ray-backed path. Ray's generated trial
set remains the population authority; ClanBasedTuning should not mirror it with
an independent runtime count that can disagree.

The complete population must be concurrently resident whenever shared gradients
are computed. Scheduler policy alone cannot guarantee that condition because
Ray's controller also stages actors through resource management. Population
admission must therefore be checked at the orchestration boundary before any
member enters the distributed collective. Manual integration first proves the
contract; the usability milestone later automates it.

The framework-independent controller may know the expected completeness rule for
its input, but that does not make it the owner of live population membership or
resource admission.

## Data and fitness

Training data retains normal distributed partitioning owned by Lightning and
PyTorch. Fitness data compares divergent candidate models, so every member must
evaluate the same held-out workload under equivalent conditions.

Each fitness value remains member-local until population comparison. A DDP metric
reduction would combine candidate scores and erase the population signal. The
complete integration must define and prove the supported sampler, transform,
ordering, loader-length, boundary, and reporting contract.

## Shared-gradient execution

PyTorch's native distributed strategy should own ordinary shared-gradient
execution. For the first complete integration, DDP is the relevant substrate: it
can synchronize an initial common state and reduce gradients while local
optimizer states and hyperparameters subsequently produce divergent parameters.
Runtime synchronization, including buffer behavior, must not erase that intended
divergence.

The accepted P6 principle is native ownership of ordinary distributed mechanics,
not a permanent one-process-per-member implementation. Later FSDP or other
Lightning-native sharding support must preserve the same Clan semantics through
the framework's native lifecycle.

## Failure and completion

An active Clan is one complete population participating in a shared-gradient
workflow. Loss of a required member invalidates that active Clan; continuing with
a smaller population changes both the distributed world and the scientific
method.

Planned completion likewise applies to the complete Clan and occurs at a
coherent population boundary. The controller must not manufacture a valid
population decision from incomplete input. The integration must terminate or
invalidate broken distributed execution clearly. The industry milestone later
qualifies operational diagnosis and recovery for its declared support envelope.

These are cumulative applications of one accepted collective-validity rule, not
three separate recovery subsystems.

## Decision alignment summary

| Decision | Alignment result |
| --- | --- |
| P1 — one Tune trial per live member | Accepted; retained. |
| P2 — Lightning round boundary | Accepted; retained. |
| P3 — controller and Ray invocation form | Revised: Milestone 2 owns the independent policy; Milestone 3 chooses the Ray seam. |
| P4 — parent selection and state execution | Accepted: ClanBasedTuning selects; Ray assigns; Lightning restores. |
| P5 — partitioned training/comparable fitness | Accepted; retained. |
| P6 — native distributed ownership | Accepted core; later native sharding remains possible. |
| P7 — collective failure/completion | Accepted core; detailed recovery remains with owning support milestones. |

The accepted decision text is in
[project decisions](../decisions/project_decisions.md). Source and probe support
is preserved in the [evidence ledger](evidence_ledger.md). Completion obligations
belong to the [milestone gate system](../milestones/README.md), and implementation
boundaries are reviewed through the
[standing framework-native review](../reviews/framework_native_review.md).
