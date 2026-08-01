# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient
training with member-local optimizer hyperparameters and population selection.

## Current implementation surface

The active package contains framework-independent pieces only:

- `ClanController` stores one finite local fitness, invokes a provisional population-
  fitness callback, selects one checkpoint source, and caches the local save decision.
- `MutationSpec` defines one bounded mutation rule for the future CBT Tune scheduler.
- `select_winner_id()` defines stable minimizing/maximizing selection and tie behavior.
- `scheduler_types.py` contains dictionary aliases only.

`MutationSpec` and `select_winner_id()` live in `evolution.py`. The obsolete
`controller_types.py` metadata builder has been removed.

## Accepted architecture

One live Tune trial represents one stable Clan member. The complete population trains
through one Lightning DDP world.

At a completed generation boundary, every member contributes one comparable local
fitness through a Ray collective population-resolution step. The complete population
must agree on exactly one stable member that may retain and report the checkpoint before
Tune reporting.

The local save decision is cached. Later checkpoint-provenance checks must not enter a
second collective.

The CBT Tune scheduler remains authoritative over population genomes, mutation, lineage,
recovery, target configurations, and checkpoint redistribution. Lightning and PyTorch
own training, gradient reduction, optimizer continuation, and checkpoint construction.

The selected worker will later record this minimal producer metadata before reporting:

```python
{
    "clan_based_tuning": {
        "schema_version": 1,
        "member_id": member_id,
        "genome": dict(genome),
    }
}
```

That metadata is evidence of the producer, not child-genome authority.

## Provisional boundary

The current controller accepts:

```python
exchange_fitness(local_fitness) -> Sequence[float]
```

and treats sequence position as member identity. That callback name, data shape, identity
contract, validation placement, and responsibility split are provisional implementation
evidence rather than accepted API design.

The architecture is committed to Ray collectives. The exact Ray primitive, exchanged
result shape, member/rank representation, controller-versus-runtime collaborator
boundary, names, timeout behavior, and generation-isolation mechanism remain under
review.

The active package does not yet contain:

- an accepted Ray population-resolution runtime;
- controller genome snapshot or `save_genome()`;
- `make_cbt_controller()`;
- the CBT Tune scheduler;
- Lightning DDP integration; or
- a repeated end-to-end generation path.

Read [`STATUS.md`](STATUS.md) for the durable project position.

## Documentation

- [`docs/product_roadmap.md`](docs/product_roadmap.md) — governing product meaning and
  milestone sequence.
- [`docs/decisions/project_decisions.md`](docs/decisions/project_decisions.md) — accepted
  technical decisions.
- [`docs/design/system_architecture.md`](docs/design/system_architecture.md) — complete
  Milestone 3 lifecycle and state ownership.
- [`docs/design/population_resolution.md`](docs/design/population_resolution.md) — fixed
  Ray population invariants and open interface choices.
- [`docs/design/behavioral_test_contracts.md`](docs/design/behavioral_test_contracts.md) —
  observable acceptance behavior.
- [`docs/controller/README.md`](docs/controller/README.md) — current controller state and
  redesign boundary.
- [`docs/framework_alignment/README.md`](docs/framework_alignment/README.md) — accepted
  framework research.
- [`AGENTS.md`](AGENTS.md) — contributor and coding-agent entry point.

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
