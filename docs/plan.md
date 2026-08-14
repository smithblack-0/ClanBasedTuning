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

Finish and review the first public repeated function-API workflow, then qualify only the
support boundary established by direct evidence.

## Work sequence

### 1. Finish the repeated function-API contract

The live contract must continue to prove, together rather than as isolated seams:

- the complete configured Clan becomes one DDP cohort;
- distinct member-local work produces a common reduced gradient;
- member-local fitness remains distinct for selection;
- exactly one member persists the round continuation;
- persistent CBT checkpoint writes remain one per round rather than one per member;
- Ray assigns the selected checkpoint and new genomes through the synchronous PBT
  lifecycle;
- resumed user code restores inherited optimizer history and explicitly applies the new
  genome; and
- the same public path reaches a later generation successfully.

Any framework failure discovered here is repaired at the narrowest native seam. Do not
add a package-owned optimizer applier, Trainer, Trainable lifecycle, training loop,
process-group lifecycle, or backend choice.

### 2. Publish the mechanics example

Once the repeated contract passes, add one small public example using the same public
objects and the same explicit userspace genome application pattern as the contract.

The example must show the application body rather than hiding it behind an unexplained
placeholder. It should make these handoffs visible:

```text
Tune genome
→ user constructs or restores training state
→ user applies current genome
→ ordinary Lightning fit
→ Clan validation/report boundary
→ selected checkpoint + mutated genomes through Tune
→ next function invocation
```

The example is mechanics evidence, not a scientific superiority claim.

### 3. Align active documentation and qualification

Bring README, status, integration design, API documentation, and qualification records
into agreement with the executed function path.

In particular, remove stale statements that CBT owns member-local optimizer application,
that the Tune scheduler remains unimplemented, or that the production path selects a
specific distributed backend.

Document the first directly qualified support boundary precisely. Adjacent accelerators,
backends, topologies, optimizer layouts, recovery modes, and storage systems are not
claimed merely because the implementation is backend-neutral.

### 4. Adversarial usability and framework review

Review the public workflow from a user who already knows Ray Tune and Lightning:

- the Tune function should receive an ordinary genome dictionary;
- private Clan topology must not appear as user genome fields;
- no backend or rendezvous setup should be required in ordinary use;
- no CBT optimizer schema or optimizer application callback should exist;
- population size must not multiply persistent round-checkpoint storage; and
- unusual user optimizer/application code must remain possible because CBT never
  interprets the genome.

Separately review every custom Ray and Lightning seam against the pinned framework source
and the standing framework-native review. Remove custom machinery when native behavior
already supplies the required contract.

### 5. Expand evidence only when needed

After the initial public path is accepted, qualify additional devices, backends, storage,
recovery, and optimizer arrangements through focused evidence rather than inference.

Complete-cohort resource admission beyond the current fixed concurrently resident path is
also a later operational improvement unless the initial usability review shows it blocks
the supported workflow.

## Later ClanFSDP work

Model-sharded Clan execution is not part of the initial DDP completion path. Near the end
of the project, a separate ClanFSDP design and qualification effort may introduce a
composed topology that represents both model shards and Clan members while retaining
framework ownership of distributed groups.

The initial implementation must not pre-build that future topology or use it to justify a
second population communication system.

## Completion boundary

This plan is complete when the first supported function-API integration repeatedly
performs Clan Tuning through the public path and its implementation, tests, qualification
records, documentation, and example agree.

Broader device/backend support, flexible cohort admission, ClanFSDP, additional optimizer
layouts, operational recovery, and scientific workloads remain later work unless direct
usability or correctness evidence makes one of them necessary for that first supported
path.
