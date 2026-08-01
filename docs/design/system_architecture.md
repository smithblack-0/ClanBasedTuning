# ClanBasedTuning system architecture

Status: active Milestone 3 system design  
Date: 2026-07-31  
Framework basis: PyTorch 2.10.x, Lightning 2.6.x, Ray Tune 2.56.x

## System result

ClanBasedTuning keeps the ordinary Ray Tune function lifecycle.

One live Tune trial represents one stable Clan member. Those trial processes form one
Lightning DDP job for a training round. Lightning DDP supplies the same reduced gradient
to every member, while each local optimizer applies that gradient using the controlled
hyperparameters assigned to that member.

The CBT Tune scheduler is the evolutionary authority. It owns population-result
collection, winner verification, mutation, next-member assignments, mutation random
state, replay lineage, recovery state, and selected-checkpoint redistribution.

The live workers use a Ray collective at the completed-round boundary so exactly one
member knows, before Tune reporting, that it may retain and report the checkpoint.

The selected checkpoint carries the common Lightning training continuation. Before
reporting it, the selected worker records the stable member ID and copied genome that
produced that continuation.

CBT defines no package-owned `Trainable` subclass, no independent training loop, no
public `ClanRound`, and no second checkpoint format.

## Governing worker flow

The accepted user-facing ordering is:

```text
read this member's scheduler-assigned genome from Trial.config
→ construct the worker controller with a copied genome snapshot
→ obtain any Tune-assigned checkpoint
→ restore model, optimizer history, and Lightning progress
→ apply the current member genome
→ train and evaluate through Lightning
→ provide one local fitness to the controller
→ participate in one Ray population-resolution operation
→ cache whether this stable member is the checkpoint source
→ every Lightning rank enters the checkpoint boundary
→ selected member retains and annotates the checkpoint
→ report metrics, with a checkpoint only from that member
```

The exact constructor and Ray-collaborator API are not yet accepted. The current
`exchange_fitness` callback is transitional code, not the governing interface.

## State authority

The word **genome** means the subset of Tune configuration fields controlled by CBT,
for example learning rate, optimizer betas, or weight decay.

| State | Authority | Copies or evidence |
| --- | --- | --- |
| Population genomes and next-generation assignments | CBT Tune scheduler | Materialized in each target `Trial.config` |
| Current member genome | That member's scheduler-assigned `Trial.config` | Controller-owned copied mapping for provenance |
| Local fitness | The evaluated member until reporting | Contributed once to Ray population resolution |
| Checkpoint-source result | Successful Ray population-resolution boundary | Cached local Boolean in each worker controller |
| Mutation RNG, replay lineage, and recovery state | CBT Tune scheduler persistence | Optional audit records |
| Model, optimizer history, and training progress | Selected Lightning checkpoint payload | Restored into every next member |
| Genome that produced the selected payload | Winning checkpoint metadata | Verified against the winner's active `Trial.config` |

The Ray collective coordinates the live workers. It does not become authoritative over
genomes or future generations.

## Ray population resolution

The architecture commits to a Ray collective across the complete live population.

The successful boundary must:

- include every configured member exactly once;
- associate one valid local fitness with each stable member;
- prevent cross-generation mixing;
- apply the same deterministic selection and tie policy used by the scheduler;
- yield the same selected stable member to every participant;
- let exactly one member retain the checkpoint; and
- fail the complete boundary if participation or data is invalid.

The architecture deliberately does not yet choose:

- the exact Ray collective primitive;
- whether the result exposed to the controller is the member-associated population or
  the selected stable member ID;
- whether stable member identity is represented by proven Ray rank equality or explicit
  identity data;
- the final controller/runtime collaborator boundary;
- the final names of that collaborator and its operations; or
- the timeout and surfaced failure types.

Those choices are refined in
[Ray population-resolution design](population_resolution.md) and require direct evidence
against the pinned Ray version.

A later query of the local save decision, including the guard inside checkpoint
provenance writing, must use the cached result and must not repeat the Ray collective.

## Selection policy

Winner selection is a framework-independent evolution policy.

It defines:

- minimizing or maximizing;
- stable tie behavior;
- fitness validity required by policy; and
- the selected stable member ID.

The worker-side Ray path and Tune scheduler verification use the same pure policy. There
must not be separate nearly equivalent comparison implementations.

The current accepted module for this pure policy is `evolution.py`. A separate
`selection.py` module is not required.

## Controller boundary

The controller is ephemeral and exists for one worker invocation and one reporting
boundary.

Its intrinsic responsibilities are:

- own one copied current-member genome mapping for provenance;
- accept one local fitness;
- participate in one Ray population-resolution boundary through the Ray integration;
- cache the local checkpoint-source answer; and
- allow only the selected member to write producer metadata.

It does not own:

- Ray group creation details exposed to the user;
- mutation or child-genome derivation;
- scheduler lineage or recovery;
- Tune checkpoint redistribution;
- Lightning checkpoint construction; or
- serializable continuation of itself.

The current constructor fields `population_size`, `mode`, and `exchange_fitness` are not
accepted merely because they exist. Their replacement must follow the reviewed Ray
runtime design rather than a rename-only refactor.

## Winning checkpoint metadata

The selected worker annotates the completed Lightning checkpoint before `tune.report()`.
The intended producer record is:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

The controller does not write:

- a round or generation index;
- a Tune trial ID;
- fitness;
- child genomes;
- mutation random state; or
- scheduler lineage.

Those are scheduler facts or unnecessary provenance fields.

The genome mapping must be independently copied when the controller is constructed. The
accepted contract is ownership of a separate mapping snapshot, not deep immutability of
arbitrary nested `object` values.

A metadata-write failure prevents checkpoint publication. The scheduler later verifies
the metadata against the selected winner and its active `Trial.config`.

## Scheduler generation transition

After all workers report, the scheduler:

1. waits for one result from every required trial;
2. associates each fitness with that trial's stable member and active genome;
3. applies the shared pure selection policy;
4. verifies that exactly the selected member reported a checkpoint;
5. verifies the checkpoint producer metadata against the selected member and genome;
6. derives one child genome per stable target member;
7. advances and persists mutation, lineage, replay, and recovery state;
8. installs every child genome in its target `Trial.config`;
9. assigns the same selected checkpoint to every target; and
10. releases the complete next population together.

No next-round worker may run from a partially committed transition.

## Atomicity boundaries

There are two distinct commit boundaries.

### Winner artifact

```text
Lightning constructs checkpoint
→ selected worker attaches producer metadata
→ selected worker reports one complete artifact
```

An unannotated winning checkpoint is not published.

### Scheduler transition

```text
collect complete Tune generation
→ verify winner and checkpoint
→ derive all child genomes
→ persist scheduler transition state
→ assign all configs and checkpoints
→ release complete next population
```

A crash before completion restores the last committed generation or fails the
experiment. It must not release a mixed population.

## Lightning DDP ownership

Lightning owns Trainer execution, optimizer lifecycle, checkpoint construction,
distributed barriers, and process-group integration. PyTorch DDP owns native gradient
reduction.

The CBT integration must preserve intended member divergence:

- retain native initial synchronization;
- retain gradient synchronization;
- disable forward-time persistent-buffer broadcast where it would overwrite local
  member state;
- do not synchronize parameters or optimizer history after local optimizer updates; and
- restore optimizer history before applying the receiving member's assigned genome.

The Ray population-resolution collective is a separate Clan-level coordination path. It
must not be silently replaced by the PyTorch process group.

## Failure boundaries

### Missing or invalid Ray participant

A missing, failed, duplicated, or cross-generation participant invalidates the complete
population boundary. Waiting work must be released through failure or timeout rather
than hanging indefinitely or selecting from a partial population.

### Invalid fitness or identity

Non-finite fitness, duplicate stable identity, incomplete identity mapping, or
inconsistent selected-member results invalidate the boundary before a save decision is
cached.

### Missing or multiple checkpoints

The scheduler requires exactly one checkpoint-bearing report, and it must belong to the
scheduler-selected winner.

### Producer metadata disagreement

The recorded member ID and genome must match the selected winner and the controlled
subset of its active `Trial.config`.

### Partial next-population assignment

No next member begins until every target has its assigned child genome, the same selected
checkpoint, and the corresponding durable scheduler state.

## Module responsibilities

The intended package organization is responsibility-based:

```text
controller.py
    worker-local boundary state, cached save decision, later producer metadata

evolution.py
    MutationSpec, deterministic winner selection, pure child-genome logic

scheduler_types.py
    dictionary aliases only

scheduler.py
    Tune generation transition, mutation state, lineage, recovery,
    target config installation, checkpoint assignment

Ray runtime integration module — final name pending
    collective group, membership, population-resolution transport,
    timeout and failure behavior, controller construction
```

The design does not commit to `ray_collective.py`, a specific collaborator class, or a
raw callback signature before the Ray interface review.

## Current implementation status

The active package currently contains:

- a framework-independent `ClanController` with one local fitness and a cached save
  decision;
- a provisional `exchange_fitness(local_fitness) -> Sequence[float]` callback contract;
- `MutationSpec` and `select_winner_id()` in `evolution.py`; and
- dictionary aliases in `scheduler_types.py`.

The active package does not yet contain:

- an accepted Ray population-resolution implementation;
- controller genome snapshot or `save_genome()`;
- `make_cbt_controller()`;
- the CBT Tune scheduler;
- Lightning DDP integration; or
- a repeated end-to-end generation path.

The provisional controller callback must be redesigned from the intrinsic requirements
before provenance work resumes.

## Initial support boundary

The first executable qualification remains narrow:

- one process and one device per Tune trial;
- one fixed, concurrently resident population;
- one Lightning DDP world;
- one Ray population-resolution collective over the same stable members;
- equal-length training participation;
- equivalent held-out fitness data;
- one supported optimizer mapping for controlled values;
- no competing learning-rate scheduler for those values;
- no elastic world-size change, SyncBatchNorm, FSDP, or model sharding; and
- no CBT or user-defined `Trainable` subclass.

These are evidence limits rather than permanent architectural claims.
