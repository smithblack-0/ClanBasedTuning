# ClanBasedTuning architecture

Status: accepted Milestone 3 architecture  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## System result

One live Ray Tune trial represents one Clan member. The concurrently resident trials form one Lightning DDP world for a training round.

Lightning and PyTorch provide ordinary training, validation, gradient synchronization, optimizer state, checkpoint construction, and restoration. ClanBasedTuning adds the population behavior needed to preserve member-local optimizer variation, compare the complete population, continue from one selected training state, and assign the next optimizer genomes.

ClanBasedTuning defines no package-owned `Trainable`, second training loop, public `ClanRound`, or second checkpoint format.

## Ordinary Tune function

The intended user lifecycle remains an ordinary Tune function:

```text
read the scheduler-assigned genome from config
→ construct the worker controller
→ obtain any Tune-assigned checkpoint
→ restore model, optimizer history, and training progress
→ apply this member's current genome
→ train and evaluate through Lightning
→ give local fitness to the controller
→ resolve whether this member is the checkpoint source
→ every DDP rank enters the Lightning checkpoint boundary
→ selected member retains and annotates the checkpoint
→ report metrics; only the selected member reports the checkpoint
```

The user does not manually coordinate collective membership, population fitness, winner policy, scheduler mutation state, or checkpoint redistribution.

## State authority

| State or decision | Authority |
| --- | --- |
| Product population policy and next genomes | CBT Tune scheduler |
| Active genome for one member | Controlled subset of that trial's `Trial.config` |
| Model, optimizer history, and training progress | Lightning checkpoint payload |
| Shared training gradients | PyTorch DDP |
| Population fitness transport before reporting | Ray population runtime |
| Winner comparison and tie behavior | Shared framework-independent selection policy |
| Local pre-report save decision | Worker `ClanController` cache |
| Genome that produced the selected payload | Winning checkpoint metadata |
| Mutation RNG, lineage, recovery, and target assignment | CBT Tune scheduler persistence |

Checkpoint producer metadata is evidence about the selected payload. It is not another source of future genomes.

## Worker controller

One controller exists for one worker invocation and one reporting boundary. It owns:

- stable local member identity and comparison mode;
- one local fitness value;
- one invocation of the Ray population runtime;
- application of the shared selection policy;
- one cached local save decision; and
- later, an independent copy of the active genome and winner-only producer annotation.

It does not construct collective groups, mutate genomes, derive children, advance generations, persist scheduler state, construct checkpoints, or report to Tune.

The accepted user-facing sequence is:

```python
controller.set_fitness(fitness)
should_save = controller.should_save_checkpoint()

if should_save:
    checkpoint = controller.save_genome(checkpoint)
```

The exact internal constructor and collaborator types are implementation details.

## Ray population runtime

The Ray-specific runtime owns the population communication boundary:

- group construction, membership, and teardown;
- stable-member-to-participant association;
- one complete-population operation at a qualifying boundary;
- generation isolation;
- transport validation; and
- surfaced communication, participant, timeout, and incomplete-boundary failure.

It returns complete member-associated fitness information. It does not select the winner or own evolution policy.

## Selection policy

One framework-independent implementation owns minimizing or maximizing behavior, comparable-input requirements, deterministic tie handling, and selected stable member identity.

Workers and the Tune scheduler apply the same implementation independently. The Ray runtime must not duplicate this policy.

## Tune scheduler

The CBT Tune scheduler is the evolutionary authority. For a complete generation it:

1. waits for one result from every required trial;
2. associates each result with the correct stable member and active genome;
3. independently selects the winner;
4. verifies that exactly the winner supplied a checkpoint;
5. verifies checkpoint producer metadata;
6. derives one child genome per target;
7. persists mutation RNG, lineage, recovery, and transition state;
8. installs each child genome in its target `Trial.config`;
9. assigns the same selected checkpoint to every target; and
10. releases the next population only after the complete transition is committed.

A partial assignment is not a generation.

## Checkpoint and genome ordering

At generation start, every member restores the same selected model, optimizer history, and training progress. The target member's current genome is then applied to the restored optimizer without clearing inherited history.

At generation end, every DDP rank enters the Lightning checkpoint boundary. Only the selected member retains a persistent continuation.

The selected member annotates the checkpoint before publication with the minimal producer record:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": copied_genome,
    }
}
```

The controller does not write generation identity, Tune trial identity, fitness, child genomes, mutation state, or lineage because those are scheduler facts.

A failed metadata write prevents the checkpoint from being reported.

## Generation transition

```text
common selected checkpoint + member-local assigned genome
→ restore common training continuation
→ apply local genome
→ DDP produces shared gradients
→ local optimizers produce diverging members
→ equivalent held-out evaluation produces local fitness
→ Ray population operation returns complete member-associated fitness
→ every worker applies the shared selector
→ exactly one member retains and annotates the checkpoint
→ Tune receives one complete result per member
→ scheduler verifies, mutates, persists, assigns, and releases together
```

The lifecycle must repeat for later generations. A controller is not itself continued across the transition.

## Failure boundaries

- Missing, duplicated, malformed, failed, or cross-generation population participation invalidates the boundary.
- A partial population cannot select a parent or advance.
- Waiting participants must eventually receive a surfaced failure rather than hang indefinitely.
- A missing, extra, losing, or metadata-inconsistent checkpoint invalidates the scheduler transition.
- A scheduler crash before complete transition commit restores the last completed generation or fails the experiment; it does not release partial targets.
- Lightning checkpoint failure and Ray communication failure remain owned by their respective integration boundaries.

## Support and evidence

Architecture does not prescribe Ray backend, device placement, dtype, internal result container, exact timeout, or internal class names when those choices do not change the contracts.

Actual support claims are bounded by direct framework and hardware qualification recorded with the current implementation decision.
