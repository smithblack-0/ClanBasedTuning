# Worker-side Clan controller

Status: active worker checkpoint-decision contract

## Purpose

`ClanController` hides the one unusual operation a normal Tune function needs before
reporting: every live Clan member must exchange fitness and agree which process is
allowed to attach the continuation checkpoint.

The controller is not the evolutionary policy owner. The Tune scheduler owns parent
selection, mutation, next-trial configuration, replay state, and winner-checkpoint
assignment. The training function continues to use Tune's ordinary checkpoint API.

## Intended Tune function

The ordinary user flow is:

```python

def train(config):
    controller = make_cbt_controller()

    model, optimizer = build_training_objects(config)

    checkpoint = tune.get_checkpoint()
    if checkpoint is not None:
        restore_training_state(checkpoint, model, optimizer)

    apply_optimizer_config(optimizer, config)
    train_one_round(model, optimizer)
    metrics = evaluate(model)

    controller.set_fitness(metrics["fitness"])
    should_save = controller.should_save_checkpoint()

    checkpoint = distributed_checkpoint_boundary(
        model=model,
        optimizer=optimizer,
        persist=should_save,
    )

    if should_save:
        tune.report(metrics, checkpoint=checkpoint)
    else:
        tune.report(metrics)
```

`distributed_checkpoint_boundary()` represents the Lightning integration: every DDP
rank participates in the required checkpoint boundary, while only the selected rank
retains and reports a persistent checkpoint.

The future `make_cbt_controller()` integration factory will obtain rank, population
size, comparison direction, and Ray collective context from CBT runtime metadata. The
user should not manually assemble those values in the train function.

## Controller responsibility

A controller exists for one Tune function invocation and one reporting boundary. It:

1. stores one finite local fitness;
2. enters one injected population-wide fitness exchange;
3. applies the configured comparison and stable rank tie-break;
4. caches whether this process is the checkpoint source; and
5. returns that boolean to the train function.

It does not own:

- model, optimizer, or Lightning state;
- Tune checkpoint loading or reporting;
- hyperparameter mutation;
- next-trial configuration;
- scheduler persistence or replay;
- a current or next `ClanRound`;
- round advancement; or
- serializable controller state.

## Core contract

The current framework-independent constructor is the integration seam:

```python
controller = ClanController(
    member_id=rank,
    population_size=world_size,
    mode="min",
    exchange_fitness=all_gather_fitness,
)
```

`exchange_fitness(local_fitness)` must block until every required member participates
and then return one rank-ordered fitness value per member.

```python
controller.set_fitness(local_fitness)
should_save = controller.should_save_checkpoint()
```

The first `should_save_checkpoint()` call performs the exchange. Later calls return the
cached result and do not enter the collective again.

## Why no `ClanRound`

The earlier active design stored configuration, fitness, population loading, winner
selection, mutation, and next-round construction across `ClanRound` and a persistent
controller. That design duplicated responsibilities now owned naturally by Tune's PBT
lifecycle.

The current worker needs only one local fitness and one collective save decision. A
separate round object would not own enough independent behavior to justify another
public lifecycle abstraction.

## Mutation rules

`MutationSpec` remains a framework-independent value used by the future CBT Tune
scheduler. It does not belong to the worker controller. The scheduler will apply those
rules when constructing each trial's next Tune configuration.

See [API reference](api.md) for the concrete active call surface and
[system architecture](../design/system_architecture.md) for the complete Tune,
Lightning, and collective lifecycle.
