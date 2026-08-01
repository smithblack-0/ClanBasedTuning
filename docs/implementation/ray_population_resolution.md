# Initial Ray population-resolution implementation

Status: accepted and partially implemented initial decision  
Framework basis: Ray 2.56.1, PyTorch 2.10.x

## Authority

This document chooses the first implementation of the accepted
[population-resolution invariants](../contracts/population_resolution_invariants.md) and
[responsibility boundaries](../contracts/population_resolution_responsibilities.md).

It is not architecture. A later implementation may replace any choice here without
reopening those contracts, provided the replacement preserves them and is qualified
directly.

## Implemented decision

The internal Ray population runtime uses `ray.util.collective.allgather` over a persistent
GLOO collective group.

Each live member contributes one scalar fitness. The runtime returns a complete mapping
from stable member identity to fitness. `ClanController` applies the shared deterministic
selection policy and caches whether its local member is the selected checkpoint source.
The Ray runtime does not select the winner.

The runtime is internal. The accepted public `make_cbt_controller(genome=...)` factory and
its automatic worker wiring are not implemented by this slice.

## Identity mapping

Collective rank is transport state, not stable member identity.

The runtime receives one ordered `member_ids_by_rank` mapping for the complete configured
population. It derives its local collective rank from that mapping and translates the
all-gather result back into a stable-member-keyed mapping before returning it to the
controller.

The implementation therefore does not depend on stable member ID and collective rank
having the same value. Incidental Ray buffer order is not exposed as controller meaning.

## Transport precision and device

The implemented path uses:

- Ray GLOO;
- CPU tensors; and
- `torch.float64` scalar fitness.

CPU transport keeps the population collective independent of the model-training device.
`float64` preserves Python-float comparison behavior for the qualified path and avoids an
unjustified narrowing to `float32` that could change the selected member for close values.

These are choices of the initial implementation, not architectural requirements. Another
backend, device, or representation may be introduced when direct evidence shows that it
preserves member association and selection semantics.

## Group lifecycle

The complete population joins one collective group before entering a population boundary.
The same initialized group may serve consecutive boundaries for the same stable live
population. The worker integration destroys it when that population ends.

`ClanController` does not initialize or destroy collective groups. It receives the
population runtime and invokes only the semantic resolution operation.

A group must not be reused across a membership change. Elastic membership and world-size
changes remain unsupported.

## Operation timeout and actor failure

Ray 2.56.1 applies `gloo_timeout` to its rendezvous metadata wait, but its GLOO wrapper
does not pass an operation timeout into the underlying torch distributed collective.
Consequently, a member that never enters an already initialized all-gather can otherwise
leave its peers blocked indefinitely.

The runtime therefore executes each all-gather on a daemon thread and waits for the
configured population-boundary timeout. If the operation is still blocked, the runtime
exits the current Ray actor. The actor failure is visible to Ray and prevents the worker
from reporting a checkpoint or continuing as a reduced Clan.

This is the first qualified failure mechanism for Ray 2.56.1. A future Ray version or
backend with a native cancellable collective may replace it without changing the
population-resolution contracts.

The runtime does not retry the failed operation as though the same generation remained
valid. Recovery belongs to the enclosing CBT scheduler and experiment lifecycle.

## Result validation

Before communication, `ClanController` rejects non-finite local fitness.

After communication, it requires:

- exactly one entry for every configured stable member;
- no unconfigured member;
- finite gathered fitness; and
- deterministic selection through the shared policy.

Malformed or incomplete member association fails before a save decision is cached.

## Public and internal surfaces

This implementation adds no package-root export. The concrete runtime class, its
constructor, lifecycle methods, timeout mechanism, rank mapping container, and transport
buffers remain internal.

The implementation must ultimately support the accepted
`make_cbt_controller(genome=...)` flow. That factory will hide stable identity,
population membership, group naming, collective construction, and comparison wiring from
the ordinary user.

## Qualified evidence so far

The retained Ray framework contract exercises:

- three live Ray actors;
- GLOO on CPU;
- an explicit rank order different from stable member order;
- adjacent Python `float64` values that would expose unsafe narrowing;
- minimizing and maximizing selection with a stable tie;
- cached controller decisions;
- two consecutive boundaries through one initialized group; and
- one required member omitting the all-gather, causing the blocked actor to exit.

The broader support and failure evidence still required is tracked in
[`../qualification/ray_population_resolution.md`](../qualification/ray_population_resolution.md).

## Superseded seam

The previous injected callback:

```python
exchange_fitness(local_fitness) -> Sequence[float]
```

has been removed from `ClanController`. The controller now depends on a semantic
population runtime returning member-associated fitness. Framework-independent unit tests
supply a fake runtime; production wiring will supply the Ray runtime.

## Framework references

- Ray collective communication documentation:
  https://docs.ray.io/en/latest/ray-more-libs/ray-collective.html
- Ray 2.56.1 GLOO implementation inspected for rendezvous and collective timeout
  behavior:
  `python/ray/util/collective/collective_group/torch_gloo_collective_group.py`
