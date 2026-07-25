# Evolutionary population policy

Status: Milestone 2 implementation under review

`ClanPopulationPolicy` is the framework-independent population-decision component
for Clan Tuning. It compares one complete set of member results, selects the sole
parent, and emits the optimizer-configuration values for every member of the next
generation.

It does not receive or modify live optimizers. It also does not collect reports,
choose training boundaries, move model or optimizer state, manage checkpoints,
or own Ray, Lightning, or distributed execution.

## Public records

`MemberResult` contains the information the policy needs from one member:

- one scalar fitness value; and
- the member's current optimizer-configuration mapping.

A population is an ordinary mapping from string member identities to
`MemberResult` values. This shape can be assembled directly in plain Python and
is compatible with trial IDs, scalar results, and configuration dictionaries
without requiring framework-owned runtime objects.

`PopulationDecision` contains:

- the selected parent identity;
- the selected fitness value; and
- a complete mapping from every input member identity to its next optimizer
  configuration.

The decision contains configuration values only. A later execution layer decides
how those values are applied to restored optimizers.

## Built-in policy

The first built-in policy is champion-centered multiplicative exploration.

1. Fitness is compared in either `min` or `max` mode.
2. Equal fitness is resolved by the lexicographically smaller member identity.
3. The selected member is the sole parent.
4. The parent's exact optimizer configuration is retained for that member.
5. Every other member receives a copy of the parent configuration.
6. Each explicitly named numeric field is multiplied by one configured factor.

Factors are distributed across challengers before they repeat, so a population
uses the available alternatives rather than relying on independent draws that
may all choose the same value. The explicit decision seed controls factor order.
The policy retains no internal mutable state.

Only fields named in `field_factors` change. Unrelated configuration entries are
copied unchanged. Fields must exist in the selected parent's configuration and
must contain finite real scalar values. Factors must be finite, positive, and
must differ from `1.0`; the exact parent already supplies the unmodified control.

This intentionally supports simple scalar optimizer choices such as learning
rate, weight decay, or momentum. Structured values and parameter-group-specific
application belong to later optimizer-utility work rather than being inferred by
the population policy.

## Example

```python
from clan_based_tuning import ClanPopulationPolicy, MemberResult

population = {
    "trial-0": MemberResult(0.42, {"lr": 3e-4, "weight_decay": 0.01}),
    "trial-1": MemberResult(0.38, {"lr": 2e-4, "weight_decay": 0.02}),
    "trial-2": MemberResult(0.47, {"lr": 4e-4, "weight_decay": 0.005}),
}

policy = ClanPopulationPolicy(
    mode="min",
    field_factors={"lr": (0.8, 1.2), "weight_decay": (0.5, 2.0)},
)
decision = policy.decide(population, seed=17)
```

Run the complete example with:

```bash
python examples/evolutionary_policy.py
```

Read the output as a policy decision, not an executed training transition. The
selected parent identifies the model and optimizer state that later execution
must inherit. The configuration mapping states only the optimizer values each
next-generation member should receive after that inherited state is restored.

## Failure behavior

The policy refuses populations with fewer than two members, invalid identities,
non-finite fitness, non-`MemberResult` entries, missing selected-parent fields, or
non-numeric selected-parent values. A failed call cannot partially advance policy
state because the policy is stateless and returns no decision until validation
and configuration generation complete.
