# ClanBasedTuning project decisions

Status: accepted cross-milestone decisions

These decisions resolve durable choices left open by the [`roadmap`](roadmap.md). They remain authoritative until a specific conflict and replacement are accepted. Milestone gates, implementation choices, qualification claims, plans, and audit history do not belong here.

## P1. One Tune trial is one live Clan member

The complete population is concurrently resident. Every member participates in every shared training-gradient boundary and every required Clan population boundary.

Ray remains the population runtime authority. Trial count, concurrent capacity, Clan world size, and resource assignment must describe one consistent live population.

## P2. Lightning produces the evolutionary boundary

A round ends at a qualifying Lightning validation-and-checkpoint event. Lightning owns training and validation cadence; CBT consumes the event rather than maintaining another progress clock.

The active integration contract defines which events qualify and proves coherent participation.

## P3. The CBT Tune scheduler is the sole evolutionary authority

The scheduler owns association of results with active genomes, winner verification, child-genome derivation, mutation random state, lineage, recovery, target configuration, and selected-checkpoint assignment.

Framework-independent selection and mutation primitives remain separately testable. The worker controller and Ray population runtime do not become competing policy owners.

The worker controller applies the shared selector to complete population information, caches its local save decision, and later permits winner-only producer annotation. It does not derive future configurations or persist evolutionary continuation.

## P4. CBT selects and mutates; Ray transfers; Lightning restores

CBT chooses the selected parent and next genomes through its Tune scheduler. Ray executes checkpoint and configuration assignment to trials. Lightning constructs and restores training continuation.

After restoration, CBT reapplies only the receiving member's assigned optimizer genome. This does not create another checkpoint format or optimizer-construction system.

The selected worker annotates the checkpoint before publication with the stable member ID and copied genome that produced it. This is provenance, not child-genome authority.

## P5. Training data is partitioned; fitness is comparable and local

Training follows ordinary distributed partitioning. Every member is evaluated at the same logical boundary on an equivalent held-out workload.

Fitness remains local until Ray collective population resolution returns complete member-associated values. Every worker and the scheduler apply the same selection and tie policy independently.

## P6. PyTorch DDP owns shared-gradient execution

PyTorch DDP owns ordinary model wrapping, initialization, gradient bucketing, and gradient collectives wherever its qualified behavior fits. CBT may configure or narrowly specialize the boundary but does not reimplement ordinary all-reduce.

Ray collective communication separately owns Clan-level population resolution. That separation does not require one backend, payload device, dtype, or collective primitive.

## P7. Failure and planned completion are collective

Failure of one active member invalidates the active Clan. Planned completion occurs only at a synchronized population boundary and ends the complete Clan.

No supported path silently shrinks the population, continues one member independently, selects from partial results, or releases a mixed next generation. Waiting participants must receive surfaced failure rather than remain indefinitely blocked.

## Active elaboration

- [`architecture.md`](architecture.md) defines the current lifecycle and state authority.
- [`contracts/population_resolution.md`](contracts/population_resolution.md) defines the population boundary.
- [`contracts/system_behavior.md`](contracts/system_behavior.md) defines observable system outcomes.
- [`implementation/population_resolution.md`](implementation/population_resolution.md) records the replaceable initial Ray mechanism and qualification boundary.
- [`evidence/framework.md`](evidence/framework.md) preserves version-sensitive framework evidence.

Completed reasoning and review history is preserved under [`archive/`](archive/).
