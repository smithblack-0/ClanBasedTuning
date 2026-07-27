# Manual Clan Tuning integration

This guide describes the current Milestone 3 manual composition. It connects one
Ray Tune trial per Clan member to one process-local `ClanController`, one
Lightning training window per round, and one native cross-trial PyTorch DDP
process group.

The implementation and focused contracts exist, but the distributed example has
not yet run in the present socket-restricted environment. The version and
topology below are therefore the evidence target, not an accepted support claim.
Milestone 3 still requires a successful live run, scientific workload and
results, and human review before closure.

## Process-local lifecycle

Every member process performs the same local sequence. No process invokes a
population-level coordinator object.

1. Ray assigns the prior winner's Lightning checkpoint and this member's next
   controller and optimizer state.
2. Lightning restores the winner's model, optimizer history, and progress.
3. `MemberStateRestore` restores this member's controller state and then applies
   this member's optimizer configuration.
4. The process joins a fresh cross-trial process group.
5. Lightning trains on this member's distinct batch. Native DDP produces the
   common gradient; the local optimizer applies it using member-local state and
   values.
6. Lightning evaluates the same held-out data used by every member and captures
   a local, unreduced fitness value.
7. The local controller publishes its result through callbacks, waits for the
   complete population, selects the sole winner, and derives its own next state.
8. The process returns that transition to Tune.
9. After every trial reports the same decision, the scheduler asks only the
   winner to save, pauses the population without extra checkpoints, and assigns
   the one winner checkpoint plus each target's own next state.
10. Each resumed process loads that assignment before its next training window.

The configured final round is different only after step 8: the scheduler requests
collective experiment completion after the complete final population arrives,
so no member starts an independent extra round.

## Responsibility map

| Owner | Responsibility in this path | Deliberately does not own |
| --- | --- | --- |
| `ClanController` in each trial process | Local round policy, winner selection, mutation, and random stream | Training, transport, checkpointing, or Ray lifecycle |
| `RayControllerCallbacks` and `ClanRuntimeExchange` actor | Plain-data publication, population and winner-agreement barriers, and process-group rendezvous | Winner policy, training, or state transfer |
| `ClanLightningTrainable` | Map one Tune step to one qualifying Lightning window and expose Ray save/load/reset callbacks | User model, data, Trainer policy, or population policy |
| Lightning and `MemberStateRestore` | Training/validation cadence, checkpoint contents and restore, then local optimizer reconciliation | Trial scheduling or winner selection |
| PyTorch DDP through `ClanDDPStrategy` | Initial synchronization, wrapping, gradient bucketing, and ordinary gradient collectives | Parameter averaging or optimizer-policy selection |
| `ClanTrialScheduler` and `apply_ray_transition` | Recognize one complete agreed boundary and translate it into Ray pause, checkpoint, assignment, or collective completion effects | Fitness calculation, mutation, training, or checkpoint serialization |
| Ray Tune | Trial creation, resources, actor lifecycle, checkpoint/configuration assignment, pause, resume, and termination | Clan policy |

`ClanRuntimeExchange` is a composition root for independent coordination state.
Its forwarding methods are dispatch, not a separate primary responsibility.

## Run and inspect the mechanics example

The current evidence target is Python 3.11–3.13, Ray 2.56.x, Lightning 2.6.x,
PyTorch 2.10.x, CPU BF16, Gloo, two concurrently resident trials, one process and
one Lightning device per trial.

Install both framework extras and run three rounds:

```bash
python -m pip install -e '.[ray,lightning]'
python examples/manual_clan_tuning.py --rounds 3
```

Ray must report at least two available CPUs. The example deliberately performs
the external ceremony that Milestone 4 may later remove:

- creates the shared runtime actor;
- generates exactly two members with `tune.grid_search`;
- reserves one CPU for each member and permits two concurrent trials;
- supplies the Clan scheduler and final collective boundary;
- constructs one ordinary Lightning model, optimizer, Trainer, and pair of data
  loaders per process; and
- disables Lightning checkpoint callbacks and distributed sampler replacement.

Each process trains on a different scalar target and validates against the same
target. The script prints every round, not only each trial's final row:

| Field | What it demonstrates |
| --- | --- |
| `clan_member_id`, `clan_round_index` | Stable process identity and shared logical boundary |
| `training_target` | Distinct member-local training input |
| `shared_gradient` | The common gradient produced by native DDP |
| `optimizer_lr`, `model_weight` | Local optimizer values and resulting member divergence |
| `validation_loss` | Comparable, unreduced local fitness |
| `clan_winner_id` | Sole-parent agreement |
| `clan_optimizer_config/lr` | The receiving member's next optimizer value |

The Tune result directories retain the per-round metric history and the
winner-authored Lightning checkpoints used for transitions.

## Failure and evidence boundary

Population publication and process-group rendezvous use finite timeouts. A
missing member therefore raises with the round or rendezvous context instead of
silently shrinking the Clan or waiting indefinitely. A Ray trial error
invalidates the active Clan, and planned completion is requested only from the
scheduler's complete-population boundary.

The repository currently proves individual contracts and substituted Trainable
lifecycle behavior. A real Lightning checkpoint restore has also demonstrated
model, optimizer-history, progress, controller, and optimizer-value ordering.
This environment denies the socket operations required by Ray startup and
`ProcessGroupGloo`, so it does not prove live cross-trial execution. CPU-only
evidence will not qualify GPU or multi-node behavior.

## Milestone 4 handoff

Milestone 4 may remove the ordinary user's need to assemble the runtime actor,
population/resource preflight, DDP strategy, required callbacks, Trainer
settings, and distributed data configuration individually. It must continue to
use the same lower-level primitives and preserve:

- one concurrently resident Tune trial per member;
- one process-local controller and member identity;
- native DDP shared gradients with member-local optimizer application;
- distinct training partitions and comparable local fitness data;
- winner-only checkpoint authority and target-local next state;
- restore-before-reconcile ordering;
- complete-population transitions and collective completion or failure; and
- the advanced manual path documented here.

This handoff specifies behavior and retained public depth. It does not select a
Milestone 4 factory, plugin bundle, or construction API.
