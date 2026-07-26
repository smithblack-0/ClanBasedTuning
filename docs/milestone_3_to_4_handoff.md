# Proposed Milestone 3 to Milestone 4 handoff

Status: review candidate; authoritative only after Milestone 3 acceptance

## Lower-level products

Milestone 4 may build on these accepted-manual-path responsibilities:

- `ClanController`: parent selection and local optimizer mutation;
- `ClanTuneSession`: trial membership, DDP topology, and round-result callbacks;
- `ClanControllerRestore`: controller checkpoint state and post-restore optimizer values;
- `ClanTuneReportCallback`: qualifying result and winner-only checkpoint report;
- `ClanLightningEnvironment`: externally launched topology for Lightning;
- `ClanDDPStrategy`: native cross-trial DDP constraints;
- `ClanBasedTraining`: controller-decision verification plus native PBT state assignment;
- `tune_checkpoint_path()`: Ray-checkpoint materialization for `Trainer.fit`.

These objects remain available for advanced manual composition.

## Ceremony a usability frontend may remove

The current user must explicitly align population size, Tune sample count, concurrency,
resources, and failure policy; create the trial session and controller; attach the two
callbacks, environment, and strategy; materialize the Tune checkpoint; choose
partitioned training and replicated validation data; disable actor reuse and independent
trial recovery; and configure the matching scheduler.

Milestone 4 may manufacture concrete Lightning components and validate the corresponding
Tune setup. It should return objects used directly by native framework APIs rather than
owning a second Trainer or training loop.

## Boundaries to preserve

A shorter path may not:

- replace controller policy with Ray PBT selection or mutation;
- create another training, validation, checkpoint, or gradient system;
- reduce fitness across divergent members;
- continue a partial population as a valid Clan;
- treat DDP rank zero as the selected parent; or
- make lower-level components unavailable to advanced users.

## Inherited support envelope

Until separately qualified, the proven manual path supports CPU, Gloo, one Lightning
process per Tune trial, a fixed concurrently resident population, `reuse_actors=False`,
`max_failures=0`, and the default one-optimizer/one-parameter-group applier on PyTorch
2.10.x, Lightning 2.6.x, and Ray Tune 2.56.x.

Milestone 4 may automate that envelope but may not imply GPU, multi-node, FSDP, actor
reuse, arbitrary optimizer layouts, or recovery support.

## First Milestone 4 design exercise

Write two or three complete intended user loops that manufacture these same components.
Compare natural Lightning/Tune usage, inspectability, and responsibility load before
selecting the public convenience API.
