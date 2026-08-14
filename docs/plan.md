# Active implementation plan

Status: current implementation sequence

## Authority

This plan sequences present work. It does not change the governing
[roadmap](product_roadmap.md), [system behavior](contracts/system_behavior.md),
[population invariants](contracts/population_resolution_invariants.md), or
[userspace API](api.md).

## Current baseline

The first complete Ray Tune function path is implemented and directly qualified on a
single CPU node with two members over two generations.

That path already includes:

- production stable-member/rendezvous assignment for the initial one-trial/one-rank
  topology;
- Lightning/PyTorch shared-gradient DDP over the framework-managed process group;
- member-local fitness exchange through the active Lightning strategy;
- deterministic worker and scheduler winner agreement;
- winner-only persistent CBT checkpointing while retaining Lightning's checkpoint barrier;
- synchronous Ray PBT transfer of the selected continuation;
- independent mutation of the selected parent genome for every next member, including the
  preceding winner; and
- a receiving function that restores the selected Lightning continuation and explicitly
  applies the newly assigned genome in userspace.

The real contract verifies inherited model state, optimizer momentum, and Lightning
training progress across the generation boundary. CBT owns none of the genome-application
logic used to establish that result.

## Current objective

Turn the initial qualified mechanics path into a robust and usable supported path without
changing its userspace ownership boundary or replacing framework-native lifecycle
machinery.

## Work sequence

### 1. Finish synchronization and public mechanics example

Keep the public API, design, behavioral contracts, qualification record, status, and
examples aligned with the code that actually passed.

Add a small reproducible mechanics example using the same public function API once its
validation-data arrangement is explicit enough not to teach an accidental unsupported
pattern. The example must show genome use as ordinary user code, not through a CBT helper.

### 2. Make comparable evaluation convenient and explicit

Lightning normally injects distributed samplers into validation dataloaders under DDP.
Clan selection instead needs member-local candidate fitness values that are valid to
compare.

Resolve and qualify a framework-native ordinary path for equivalent held-out evaluation.
Possible implementation work may use supported Lightning data/strategy seams, but it must
not silently rewrite arbitrary user sampler semantics without a contracted behavior.

Acceptance requires a multi-example validation test that would detect accidental
rank-specific evaluation and a documented rule against reducing the candidate fitness
metric across the Clan.

### 3. Harden complete-cohort admission and failure behavior

The initial runtime waits for the complete assigned population and has a bounded pre-DDP
rendezvous timeout, but all members must already fit concurrently on the cluster.

Investigate the smallest Ray-native mechanism for stronger gang/cohort admission if one is
needed. Qualify incomplete-resource behavior and member failure without creating a second
training scheduler or taking process-group ownership from Lightning/PyTorch.

Separately qualify what happens when a participant disappears inside an active framework
collective. Do not claim bounded recovery until the real failure path releases healthy
participants or fails the experiment predictably.

### 4. Qualify GPU execution

Run the same public path on the intended CUDA/NCCL configuration. Production code must
continue to use the backend selected by Lightning/PyTorch rather than adding a CBT backend
switch.

Evidence must cover shared gradients, member-local divergence, fitness exchange,
winner-only checkpoint persistence, full continuation restore, and repeated generation
transition.

### 5. Qualify multi-node execution

Extend the same one-member/one-rank DDP path across nodes. Resolve only topology and
rendezvous behavior actually required by the framework evidence. Do not replace the
single-node integration with a separate multi-node training system.

### 6. Expand scientific and operational evidence

Once the mechanics path is stable on the intended hardware, add realistic optimizer
studies using the public package. Establish useful round frequencies, overhead, checkpoint
cost, and optimizer-policy behavior empirically rather than inferring scientific value
from the mechanics test.

Add observability and diagnostics where real workloads expose missing information.

## Later ClanFSDP work

Model-sharded Clan execution remains a separate later design and qualification effort. It
may require a composed topology representing both model shards and Clan members, while
retaining framework ownership of the resulting process groups.

The current DDP implementation must not pre-build that topology or use it to justify a
second population communication runtime.

## Current completion boundary

The initial CPU mechanics path is complete when the synchronized documentation and
qualification record agree with a green exact-head CI run. It is not equivalent to a
broad production-support claim.

The next practical milestone is a documented, reproducible public path with comparable
evaluation and predictable cohort/failure behavior on the intended GPU environment. All
later work must preserve the same fundamental contract: CBT supplies a genome; the user
owns what happens with it.
