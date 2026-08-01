# Population-resolution contract

Status: accepted Milestone 3 contract

This contract defines the behavior and ownership of the worker-side population boundary that determines which member may report the generation checkpoint.

## Invariants

1. One live Tune trial represents one stable Clan member.
2. The complete configured Clan participates once at each qualifying generation boundary.
3. Every required member contributes exactly one comparable local fitness from that same logical boundary.
4. Each fitness remains associated with the correct stable member.
5. A successful operation contains every required member, no duplicate, and no value from another generation.
6. Every successful worker reaches the same selected-member conclusion before reporting to Tune.
7. Exactly one member may retain and report the checkpoint.
8. Repeated save-decision queries and later provenance checks perform no second population communication.
9. The scheduler independently applies the same selection policy and verifies the checkpoint source.

The population operation uses Ray collective communication. PyTorch DDP remains responsible for training-gradient communication.

## Semantic result

A successful Ray population operation returns a complete association between stable member identity and finite comparable fitness.

The concrete Python representation is not architectural. A sequence is acceptable only when its participant ordering and stable-member meaning are established by the runtime contract.

## Ownership

### Ray population runtime

Owns:

- collective-group construction, membership, and teardown;
- stable-member-to-participant association;
- communication at one qualifying boundary;
- complete member-associated output;
- prevention of cross-generation mixing; and
- surfaced initialization, timeout, participant, communication, malformed-output, and incomplete-boundary failure.

Does not own comparison direction, tie behavior, winner selection, mutation, checkpoint construction, Tune reporting, or scheduler state.

### Shared selection policy

Owns:

- minimizing or maximizing behavior;
- comparison-validity rules;
- deterministic stable tie behavior; and
- selection of one stable member from complete member-associated fitness.

The worker path and Tune scheduler use the same implementation. The Ray runtime contains no second winner policy.

### Worker controller

Owns:

- stable local member identity;
- comparison mode;
- one local fitness value;
- one Ray population operation;
- application of the shared selector;
- one cached local save decision; and
- later, copied current-genome provenance and winner-only annotation.

The controller does not construct Ray groups, expose transport buffers to the user, derive child genomes, advance generations, persist scheduler state, or report to Tune.

### Worker integration

Constructs and wires the controller and Ray runtime. It obtains member identity, population membership, comparison configuration, generation context, and collective configuration without requiring the user training function to assemble them.

The ordinary public flow remains conceptually:

```python
controller = make_cbt_controller(genome=genome)
controller.set_fitness(fitness)
should_save = controller.should_save_checkpoint()
```

The exact factory and internal collaborator signatures are implementation details.

### Tune scheduler

Waits for one result from every required trial, associates results with stable members and active genomes, independently selects the winner, verifies exactly one winner checkpoint and its producer metadata, and performs the complete evolutionary transition.

Worker agreement enables pre-report checkpointing; scheduler verification determines whether the transition is accepted.

## Failure behavior

The boundary is invalid when a required participant is missing or fails, participation is duplicated, fitness is malformed or non-comparable, identity association is incomplete, or generations mix.

An invalid boundary must not:

- select from a partial population;
- silently shrink the Clan;
- let any member report a continuation checkpoint;
- release the next generation; or
- leave healthy participants waiting forever without a surfaced failure.

Exact timeout values, cancellation mechanisms, generation-token representation, and exception types are implementation choices. Their observable outcome must satisfy this contract.

## Representation freedom

Architecture does not require:

- stable member identity to equal collective rank, only a proven unambiguous mapping;
- a tuple, list, dictionary, tensor, or dedicated object as the result container;
- CPU or accelerator payload storage;
- one floating-point dtype;
- one Ray backend; or
- one exact collective primitive when an equivalent supported composition preserves the contract.

The initial implementation decision may choose among these options and must be qualified directly.
