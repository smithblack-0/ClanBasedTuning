# Milestone 3 closure review

Status: proposed for human review; not accepted or merged

This record maps the Milestone 3 gate to the implementation and direct evidence in the
stacked review ending at PR #17. It does not itself accept the milestone.

## M3.1 — Ray invocation path

**Proposed satisfied.** `ClanBasedTraining` specializes synchronous Ray PBT only at the
policy seam. Process-local controllers choose the winner. The scheduler verifies their
agreement, preserves target construction config, and reuses native PBT pause,
checkpoint assignment, resume, and persistence.

Evidence:

- `src/clan_based_tuning/ray/scheduler.py`
- `docs/milestone_3_manual_workflow.md`
- `tests/framework_contracts/test_upstream_contracts.py`
- `tests/framework_contracts/test_ray_native_pbt_cycle.py`

## M3.2 — Native ownership

**Proposed satisfied.** Lightning owns training, validation, checkpoint contents, and
restore. PyTorch DDP owns gradient collectives. Ray owns trial execution and state
assignment. ClanBasedTuning contributes only membership/result rendezvous, controller
policy, restore reconciliation, winner-only reporting, and required cross-trial DDP
configuration.

Evidence:

- `src/clan_based_tuning/ray/session.py`
- `src/clan_based_tuning/lightning/callbacks.py`
- `src/clan_based_tuning/lightning/strategy.py`
- `src/clan_based_tuning/lightning/checkpoint.py`

## M3.3 — One live shared-gradient population

**Proposed satisfied for CPU/Gloo.** The complete population is required before
training, receives stable ranks, forms one DDP group, processes partitioned training
data, receives equal reduced gradients, and diverges through member-local optimizer
values.

Evidence:

- `tests/framework_contracts/test_native_trial_lightning_probe.py`
- `tests/framework_contracts/test_ray_native_pbt_cycle.py`

## M3.4 — Comparable round results

**Proposed satisfied.** Lightning validation is the report boundary. Validation data is
replicated, fitness remains local with `sync_dist=False`, and every process publishes
one completed `ClanRound` before comparison.

Evidence:

- `ClanTuneReportCallback`
- `replicated_sampler`
- both public examples and framework contracts

## M3.5 — Sole-parent transition

**Proposed satisfied.** Every controller sees the same population and winner. Only that
process serializes a checkpoint. Native PBT assigns it to targets. Every reconstructed
process restores the same model, optimizer, loop, and controller parent before local
mutation and optimizer reconciliation.

Evidence:

- `tests/framework_contracts/test_native_trial_lightning_probe.py`
- `tests/framework_contracts/test_ray_native_pbt_cycle.py`
- scheduler `selection_path`

## M3.6 — Collective failure

**Proposed satisfied for the supported manual path.** Population completeness is
mandatory, result waits time out, `max_failures=0` forbids independent recovery, and a
member failure invalidates the run rather than shrinking the Clan.

Evidence:

- `tests/framework_contracts/test_collective_failure.py`
- `tests/unit/test_rendezvous.py`
- scheduler admission checks

## M3.7 — Direct and framework-contract tests

**Proposed satisfied.** Focused tests cover controller state ordering, round exchange,
DDP and optimizer topology, winner-local Lightning serialization, PBT exploitation,
synchronous pause behavior, repeated native transitions, and collective failure.

## M3.8 — Repeated real rounds

**Proposed satisfied for CPU/Gloo.** The native Ray contract completes two sole-parent
transitions across two Tune trials and DDP ranks and inspects gradients, common parent,
divergence, checkpoint count, and replay path.

Evidence: `tests/framework_contracts/test_ray_native_pbt_cycle.py`.

## M3.9 — Engineering documentation

**Proposed satisfied.** The manual guide follows a round across process-local and driver
owners, explains the private Lightning checkpoint seam, lists required settings,
records limitations, and states failure behavior.

Evidence: `docs/milestone_3_manual_workflow.md`.

## M3.10 — Public mechanics example

**Proposed satisfied.** `examples/manual_cpu_clan.py` uses the public components and
prints final member state and selected-parent lineage.

## M3.11 — Initial scientific workload

**Proposed satisfied.** `examples/iris_clan_experiment.py` applies the public path to a
real classification dataset and records workload, round policy, elapsed CPU cost,
fitness, accuracy, lineage, and limitations. The neutral first result is recorded in
`docs/experiments/milestone_3_iris_initial.md`.

## M3.12 — Internal consistency

**Proposed satisfied.** Implementation, tests, manual guide, mechanics example,
scientific experiment, and stated support envelope use the same explicit composition.
The legacy factory remains labeled proof-of-concept evidence rather than the accepted
manual path.

## M3.13 — Milestone 4 handoff

**Proposed satisfied.** `docs/milestone_3_to_4_handoff.md` identifies the assembly work
a usability frontend may remove, the lower-level components it must retain, and the
support claims it may not broaden.

## Qualified support claim

The proposed evidence qualifies only:

- CPU execution;
- Gloo DDP;
- one Lightning process per Tune trial;
- fixed concurrently resident populations;
- `reuse_actors=False`;
- `max_failures=0`;
- default one-optimizer/one-parameter-group reconciliation; and
- PyTorch 2.10.x, Lightning 2.6.x, and Ray Tune 2.56.x.

## Human decision required

Milestone 3 remains open until human review accepts or corrects every gate above and
the stacked PRs are integrated intentionally. GPU, multi-node, FSDP, actor reuse,
independent recovery, and general optimizer layouts remain outside this closure claim.
