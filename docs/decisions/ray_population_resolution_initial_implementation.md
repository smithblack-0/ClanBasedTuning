# Initial Ray population-resolution implementation

Status: proposed implementation decision  
Date: 2026-07-31  
Framework basis: Ray 2.56.x

## Authority

This document chooses the first implementation of the accepted
[population-resolution invariants](../design/population_resolution_invariants.md) and
[responsibility boundaries](../design/population_resolution_responsibilities.md).

It is not architecture. A later implementation may replace any choice here without
reopening the architectural contracts, provided the replacement preserves those
contracts and is qualified directly.

## Decision

The first Ray population runtime will use `ray.util.collective.allgather`.

Each live member contributes one scalar fitness through a Ray collective group spanning
the complete active Clan. The group is constructed from the complete ordered member set
and records an explicit mapping between stable member identity and collective rank.

The implementation does not rely on rank and member identity being the same concept. It
may assign equal integer values for convenience, but it retains the mapping as runtime
state and interprets gathered values through that mapping.

Each member:

1. converts its local fitness into a one-element tensor or array supported by the chosen
   Ray collective backend;
2. allocates one receive element per collective rank;
3. performs one all-gather;
4. converts the gathered values into the semantic stable-member-to-fitness association;
   and
5. returns that complete association to `ClanController`.

`ClanController` then applies the shared `select_winner_id()` policy and caches whether
its local member is the selected checkpoint source.

The Ray population runtime does not select the winner.

## Backend and device policy

The runtime selects a Ray-supported collective backend compatible with the configured
execution device and payload representation.

The initial implementation must support both of the paths needed for qualification:

- CPU collective payloads through GLOO; and
- accelerator collective payloads through NCCL where the supported training path uses
  CUDA.

The controller and scheduler contracts are independent of that choice. Backend, tensor
library, device placement, and dtype remain runtime configuration or internal
implementation details.

Those details are acceptable only when the selected transport preserves the ordering and
comparison semantics of the supported fitness values. A transport conversion that can
change the selected member is a correctness defect.

## Group lifecycle

The worker integration constructs one Ray collective group for the complete active Clan
and gives the Ray population runtime access to:

- the complete stable member set;
- the member-to-rank mapping;
- the group identity;
- the chosen backend and payload placement; and
- failure and timeout configuration supported by that backend.

The population runtime owns group use and teardown. `ClanController` does not call Ray
collective construction APIs directly.

The same group may be reused across generation boundaries. Reuse is valid because the
scheduler does not release the next generation until the current complete generation is
accepted, and every member performs exactly one population-fitness operation per
qualifying boundary.

The implementation must still detect or surface skipped, duplicated, failed, or
misordered participation rather than accepting a mixed generation.

## Result semantics

The output to the controller is a complete association between stable member identity
and finite fitness.

The concrete Python container is internal. The implementation may use a dictionary,
sequence plus explicit rank mapping, dedicated value object, or another representation.
It must not expose incidental Ray buffer ordering as an undocumented controller
contract.

## Validation and failure

Before communication, the controller rejects local fitness that is invalid for the
selection policy.

After communication, the Ray population runtime or controller verifies:

- one gathered value for every configured collective participant;
- a complete one-to-one mapping to the configured stable members; and
- values valid for the shared selection policy.

Group initialization failure, participant failure, collective failure, timeout,
malformed output, or incomplete identity association fails the complete boundary.

The initial implementation does not retry a failed collective as though the same
population were still valid. Recovery belongs to the enclosing scheduler and experiment
lifecycle.

## Public and internal surfaces

The accepted user-facing flow remains:

```python
controller = make_cbt_controller(genome=genome)
controller.set_fitness(fitness)
should_save = controller.should_save_checkpoint()
```

This decision does not freeze the internal collaborator class name, constructor
signature, transport container, or helper-method names. Those are chosen in the
implementation PR and may change without revisiting this decision when ownership and
behavior remain unchanged.

## Why all-gather

The worker controller is responsible for applying the same framework-independent
selection policy used by the scheduler. All-gather gives every worker the complete
population information needed to apply that policy without duplicating selection inside
the Ray runtime.

The pinned Ray collective API supports all-gather for CPU/GLOO and GPU/NCCL paths and
requires an output list matching the collective world size. That directly matches the
complete-population requirement.

## Superseded implementation

The merged callback:

```python
exchange_fitness(local_fitness) -> Sequence[float]
```

is not the target interface. It lacks an explicit Ray runtime owner and leaves stable
member association implicit.

The implementation should be replaced from the responsibility contract rather than
renamed in place or copied from an older controller architecture.

## Framework reference

- Ray 2.56 collective communication documentation:
  https://docs.ray.io/en/latest/ray-more-libs/ray-collective.html
