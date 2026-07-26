# ClanBasedTuning

ClanBasedTuning is a pre-alpha research library for Clan Tuning: shared-gradient
training with member-local optimizer hyperparameters and population selection.

## Project status

The framework-independent Clan controller is the first accepted implementation
surface. The current Milestone 3 review proposes an explicit manual Ray Tune,
Lightning, and PyTorch DDP composition. It remains a review candidate until human
acceptance and must not be confused with the shorter usability frontend planned for
Milestone 4.

Read [`STATUS.md`](STATUS.md) for the current durable project position.

## Documentation

- [`docs/product_roadmap.md`](docs/product_roadmap.md) — governing product meaning,
  development criteria, and milestone sequence.
- [`docs/decisions/project_decisions.md`](docs/decisions/project_decisions.md) —
  accepted cross-milestone technical decisions.
- [`docs/milestones/README.md`](docs/milestones/README.md) — milestone-gate rules
  and links to the active gate.
- [`docs/controller/README.md`](docs/controller/README.md) — controller lifecycle,
  ownership, algorithms, and API reference.
- [`docs/milestone_3_manual_workflow.md`](docs/milestone_3_manual_workflow.md) —
  proposed process-local integration sequence, component ownership, limitations, and
  framework seam rationale.
- [`docs/experiments/milestone_3_iris_initial.md`](docs/experiments/milestone_3_iris_initial.md)
  — first integrated scientific workload and neutral result.
- [`docs/milestone_3_to_4_handoff.md`](docs/milestone_3_to_4_handoff.md) — assembly
  work a later usability frontend may remove and boundaries it must preserve.
- [`docs/milestones/reviews/milestone_3_review.md`](docs/milestones/reviews/milestone_3_review.md)
  — gate-by-gate human review record.
- [`docs/framework_alignment/README.md`](docs/framework_alignment/README.md) —
  framework research, evidence, and accepted responsibility model.
- [`AGENTS.md`](AGENTS.md) — entry point for coding agents and contributors using
  the repository's durable engineering process.

## Manual examples under review

The proposed Milestone 3 path deliberately requires explicit composition:

```bash
python -m pip install -e '.[dev,ray]'
python examples/manual_cpu_clan.py --storage-path /tmp/clan-manual
python examples/iris_clan_experiment.py --storage-path /tmp/clan-iris
```

The mechanics example exposes shared gradients, member divergence, sole-parent
selection, winner-only checkpoint creation, common restoration, local optimizer
mutation, and replay lineage. The Iris experiment applies the same public components
to a real classification dataset and records workload, cost, results, and limitations.

A future usability frontend may manufacture these same components. It must not conceal
a second scheduler, training loop, checkpoint system, or gradient implementation.

## Development

Python 3.11 through 3.13 is supported.

```bash
python -m pip install -e '.[dev,ray]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
