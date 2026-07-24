# Framework-alignment decision register

Status: proposed decisions for Milestone 1 acceptance  
Date: 2026-07-24

## Purpose and relationship to the roadmap

This register resolves framework choices left open by the governing
[product roadmap](../product_roadmap.md). After acceptance, later work may rely
on these decisions without reopening the full research record. The decisions
constrain ownership and externally meaningful behavior; they do not prescribe
class layouts or settle the detailed design of later milestones.

## D1. One Tune trial represents one live Clan member

**Decision.** One Ray Tune trial represents one Clan member. The complete
population must be concurrently resident, and every live member participates in
every shared training gradient.

**Basis.** A queued or time-multiplexed member does not contribute to the current
gradient. That would be a different stale-gradient or state-swapping method, not
a slower implementation of the same Clan round.

**Consequences.** Ray remains the population authority. Population generation,
concurrent capacity, Clan world size, and dedicated resources must describe one
consistent live population. The later assembly design owns the exact admission
check and supported search topology.

## D2. Lightning produces the round boundary

**Decision.** A Clan round ends at a qualifying Lightning validation and
checkpoint report. Lightning owns the training and validation cadence that
produces the event; the evolutionary controller consumes the event rather than
creating a second progress clock.

**Basis.** A Clan-owned epoch, batch, optimizer-step, or timer would duplicate
training-loop authority and permit two definitions of the same round.

**Consequences.** Reports that do not represent the qualifying population
boundary do not trigger evolution. Exact supported cadence and continuation
behavior belong to the Lightning integration milestone.

## D3. The evolutionary subsystem specializes synchronous Ray PBT

**Decision.** The next milestone will first implement the Clan population
transition as a narrow specialization of synchronous Ray
`PopulationBasedTraining`. If executable contract tests show that the available
seam cannot express the transition without reproducing substantial Tune
controller behavior, that evidence reopens this decision.

**Basis.** Ray PBT already owns population synchronization, source-checkpoint
preparation, checkpoint and configuration transfer, pause, and resume.
ClanBasedTuning changes the population decision, not that surrounding lifecycle.

**Consequences.** The policy selects one deterministic parent, treats the other
members as next-generation targets, preserves an elite configuration, and
restricts mutation to optimizer-side configuration. The
[evolutionary-controller plan](../milestones/evolutionary_controller_plan.md)
owns the exact policy, extension seam, tests, and failure ordering.

## D4. Ray transfers member state; Lightning defines and restores it

**Decision.** Lightning owns checkpoint contents and restoration. Ray PBT owns
source selection and assignment to target trials. After Lightning restores the
parent's optimizer state, ClanBasedTuning reapplies only the receiving member's
evolved optimizer configuration.

**Basis.** This division preserves native checkpoint lifecycles, retains the
parent's optimizer history, and still allows the next generation to diverge.

**Consequences.** The initial architecture does not add a second Clan checkpoint
scheduler or generation manifest. Every divergent member must be able to supply
a source checkpoint. The integration and optimizer-utility milestones own the
save seam, restore hook, storage behavior, and supported optimizer mappings.

## D5. Training data is partitioned; fitness data is comparable

**Decision.** Training keeps normal distributed partitioning. Every member is
evaluated on the same held-out workload under comparable conditions, and the
fitness value remains member-local until Ray performs population comparison.

**Basis.** Distinct training batches provide useful shared-gradient work.
Distinct evaluation samples would confound candidate ranking, while distributed
fitness reduction would erase the differences being ranked.

**Consequences.** Existing Lightning and PyTorch data ownership should be
preserved. The integration milestone owns the exact evaluation sampler,
reporting contract, and supported dataloader envelope.

## D6. Native PyTorch DDP owns shared-gradient execution

**Decision.** PyTorch DDP owns ordinary model wrapping, gradient bucketing, and
collectives wherever qualified behavior fits. ClanBasedTuning may configure or
narrowly specialize the framework boundary, but it does not reimplement normal
all-reduce.

**Basis.** Clan Tuning needs a common reduced gradient, not a new collective
algorithm. Native DDP is the established owner of that work.

**Consequences.** Member models must remain compatible with one DDP collective,
and framework behavior must not erase intended post-update divergence. The
integration milestone owns the exact construction seam and qualified support
envelope.

## D7. Failure and planned completion are collective

**Decision.** Failure of one active member invalidates the active Clan. Planned
completion occurs only at a synchronized population boundary and ends the
complete Clan.

**Basis.** Members jointly produce each gradient and jointly constitute one
population generation. Independent recovery, early termination, or world-size
shrinkage would leave inconsistent collective state or change the algorithm.

**Consequences.** Initial work fails or stops together rather than speculatively
repairing one member. The evolutionary-controller milestone must identify the
narrowest Ray-native owner for collective planned completion; later industry
work owns fault recovery.

## D8. Interrupted-round experiment recovery is deferred

**Decision.** Normal PBT source-to-target checkpoint inheritance is required.
Whole-Tuner restoration across an interrupted synchronous boundary is not an
initial support claim.

**Basis.** Tune may persist experiment metadata while only part of a population
boundary has reported. Independently restored trial records do not necessarily
identify one coherent Clan generation.

**Consequences.** Later recovery work must define authoritative generation state,
commit ordering, and checkpoint retention before the project claims
interrupted-round resume.

## D9. Current code is evidence, not architecture

**Decision.** Existing classes, files, helper APIs, examples, and tests have no
presumption of survival.

**Basis.** They predate the accepted framework-alignment work and may embody
proof-of-concept choices rather than durable responsibility boundaries.

**Consequences.** Reuse is justified unit by unit through the current milestone
design, direct evidence, and the standing
[framework-native engineering review](framework_native_review.md), not by
compatibility with the old API.
