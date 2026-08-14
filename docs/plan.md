# Active implementation plan

Status: current implementation sequence

## Authority

This plan sequences the present work. It does not change the
[roadmap](product_roadmap.md), the [integration design](design/integration.md), or
the [behavioral](contracts/system_behavior.md) and
[population-resolution](contracts/population_resolution_invariants.md) contracts.
Implementation evidence may change the sequence or an internal choice without changing
those authorities.

## Current baseline

The active function-API build now composes the first complete Clan path around ordinary
Ray Tune and Lightning usage:

- `ClanScheduler` specializes synchronous Ray PBT at its population-policy seam;
- `ClanScheduler.wrap(train)` supplies hidden Clan cohort context while preserving the
  user's plain `train(genome)` function signature and genome dictionary;
- `ClanDDPStrategy` supplies externally assigned Tune-member topology to Lightning while
  leaving process-group creation, backend selection, and collective execution to
  Lightning/PyTorch;
- `ClanTuneReportCallback` exchanges member-local fitness over the established DDP group,
  resolves the sole checkpoint source, and reports the round to Tune;
- only the selected member delegates the CBT round checkpoint to Lightning's
  `CheckpointIO`, although every DDP rank participates in ordinary Lightning checkpoint
  construction and its barrier; and
- `ClanController`, `MutationSpec`, and the deterministic winner policy remain the small
  framework-independent core.

Genome application is not a CBT integration responsibility. Ray supplies the newly
assigned genome to the function trainable; the user's function restores the selected
checkpoint and explicitly applies that genome to whatever training state the user means
it to control.

The real single-node CPU framework contract has exercised repeated Tune function
transitions through this path. It uses Lightning/PyTorch's automatically selected CPU DDP
backend; production CBT code does not choose GLOO, NCCL, CPU, or CUDA.

## Current objective

Human review of the completed function-API build is now the synchronization point. Do not
expand the implementation into broader support work until that userspace/API and ownership
review is complete.

## Completed build evidence

The current branch directly demonstrates:

- the complete configured two-member Clan becoming one DDP cohort;
- distinct member-local work participating in native shared-gradient training;
- member-local fitness remaining distinct for selection;
- exactly one physical Lightning `CheckpointIO` write per Clan round;
- worker and scheduler agreement on the selected member;
- scheduler verification of the actual selected Ray checkpoint producer metadata before
  redistribution;
- Ray's synchronous PBT checkpoint/configuration handoff;
- explicit userspace genome application after inherited optimizer-state restore; and
- repeated operation through the same public function path.

The public mechanics example uses that same path rather than a separate demonstration
implementation.

## Review focus

The human review should judge the system from the public behavior inward:

1. `train(genome)` remains an ordinary Ray Tune function and the genome contains no
   private Clan topology.
2. User code owns genome interpretation and application; CBT contains no optimizer
   applier or post-restore application callback.
3. `ClanScheduler` owns only the Clan population policy and delegates native
   checkpoint/configuration transfer to synchronous PBT.
4. `ClanDDPStrategy` preserves Lightning/PyTorch ownership of distributed initialization
   and backend selection.
5. Population fitness uses the already-established DDP world rather than a second
   communication backend.
6. Persistent CBT checkpoint storage is one selected continuation per round, independent
   of population size.
7. The selected checkpoint artifact itself is verified against scheduler producer state
   before it is redistributed.

If that public contract is accepted, the next implementation work should be chosen from
observed usability/support needs rather than from the previous internal milestone order.

## Qualified support boundary

The directly exercised path is intentionally narrow: Ray 2.56.1, Lightning 2.6.5,
PyTorch 2.10.0, Python 3.11 for the Ray-native contract, one machine, CPU execution, two
concurrently resident members, and repeated generation boundaries.

The implementation is backend-neutral but that does not qualify untested backends or
devices by inference.

## Later qualification and operational work

After review, likely support-expansion candidates include:

- complete-cohort/gang admission when the cluster cannot already schedule every member;
- incomplete-member and distributed failure release;
- CUDA/NCCL and other accelerator paths;
- multi-node execution;
- actor reuse and explicit distributed-context reformation;
- remote checkpoint-storage qualification;
- broader recovery behavior; and
- larger populations and realistic workloads.

These are support/operational qualifications, not reasons to move genome application into
CBT or introduce a second process-group subsystem.

## Later ClanFSDP work

Model-sharded Clan execution is not part of the initial DDP completion path. Near the end
of the project, a separate ClanFSDP design and qualification effort may introduce a
composed topology that represents both model shards and Clan members while retaining
framework ownership of distributed groups.

The initial implementation must not pre-build that future topology or use it to justify a
second population communication system.

## Completion boundary

The current build unit is ready for review when its implementation, tests, qualification
records, documentation, and example all describe the same function-API lifecycle and the
repository validation passes.

Broader support and ClanFSDP remain subsequent work after the human review boundary.
