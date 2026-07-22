# Native Tune-trial build contract

Status: authoritative implementation contract for the first Clan Based Training build

Date: 2026-07-21

## Product statement

Clan Based Training is constrained synchronous Population Based Training in which native Ray Tune trials retain ordinary trial identity, configuration, checkpoint, pause, resume, and exploit behavior while temporarily joining one DDP process group and consuming a shared reduced gradient.

For a compliant problem, the integration turns ordinary PBT optimizer mutation into cooperative optimizer tuning without replacing Ray Tune or Lightning.

## Responsibility layout

### `ClanBasedTraining`

A strict subclass of Ray's `PopulationBasedTraining`.

It retains Ray's existing ownership of:

- native Tune trials;
- perturbation clocks, scores, quantiles, and exploit/explore;
- checkpoint selection and cloning;
- trial configuration mutation;
- pause, actor recreation, and resume;
- scheduler persistence and experiment restoration.

It adds only clan constraints:

- synchronous PBT is mandatory;
- the population size is fixed;
- only declared optimizer config keys may mutate;
- all other trial configuration must remain identical;
- every trial must request one identical resource bundle;
- independent trial retries are disabled;
- stable Tune trial IDs receive stable clan ranks;
- the complete rank map is published to the rendezvous actor.

### `ClanDDPStrategy`

A focused Lightning `DDPStrategy` subclass installed inside every native Tune trial.

It owns:

- resolving the current trial's clan rank and process-group endpoint;
- preventing Lightning from launching child processes;
- forcing divergence-safe DDP behavior;
- verifying model and optimizer structural compatibility;
- synchronizing the initial fresh model exactly once;
- applying the Tune trial's optimizer fields after construction and after checkpoint restore;
- allowing every native trial to save its local Lightning checkpoint.

It does not rank trials, mutate configurations, clone checkpoints, or implement a training loop.

### `ClanBase`

A stateless construction facade. It gives the scheduler and strategy the same `ClanSpec` and supplies safe Tune/Lightning configuration helpers. It is not a controller and owns no lifecycle state.

### Rendezvous

A zero-CPU named Ray actor maps stable Tune trial IDs to clan ranks and creates a fresh process-group session for each actor generation. Actor tokens are ephemeral. The scheduler rebuilds and republishes the rank map from the native trial population when trials are added.

The durable rendezvous identity is serialized into every Tune trial config. That metadata is authoritative if a restored Tune experiment reconstructs the frontend object with a new random default name; the full `Tuner.restore` path remains an explicit integration gate.

## DDP invariants

`ClanDDPStrategy` sets these internally:

- `init_sync=False`;
- `broadcast_buffers=False` for the supported PyTorch line;
- one Lightning device/process per Tune trial;
- externally created rank and world-size information.

Explicit contradictory user values fail immediately. Omitted values are filled automatically.

Disabling `init_sync` removes PyTorch DDP's normal initial parameter broadcast and structural verification. The strategy replaces both deliberately:

1. all ranks exchange module, parameter, buffer, and optimizer schemas;
2. incompatible structures fail before DDP wrapping;
3. a completely fresh population receives one explicit rank-zero parameter/buffer broadcast;
4. checkpoint-restored populations retain their independently restored values.

## Checkpoint lifecycle

Ray remains checkpoint authority.

The existing `TuneReportCheckpointCallback` asks Lightning to construct a checkpoint and reports it to Ray. Each Tune trial has its own temporary checkpoint directory. `ClanDDPStrategy.save_checkpoint()` removes only Lightning's normal global-rank-zero write gate, allowing every native trial to produce its own checkpoint.

On exploit:

1. Ray PBT selects a source checkpoint and mutated target config;
2. Ray recreates the target trial actor from the source checkpoint;
3. user code materializes that checkpoint through `ClanBase.tune_checkpoint_path()`;
4. Lightning restores model, optimizer, progress, and callback state;
5. `ClanDDPStrategy.load_optimizer_state_dict()` reapplies the target trial's mutated optimizer values;
6. all trials form a fresh process group for the next window.

If Ray supplies a checkpoint but Lightning is started without `ckpt_path`, the strategy fails rather than silently restarting the member from scratch.

## Data contract

Training data should retain Lightning's ordinary distributed sampler behavior. Each member therefore consumes a different shard/minibatch while participating in the common gradient reduction.

Fitness data must be comparable across members. `ReplicatedDistributedSampler` gives every member the same deterministic validation examples and is preserved by Lightning because it is already a `DistributedSampler` instance.

Fitness metrics must be logged with `sync_dist=False`; distributed metric reduction would erase member identity before PBT sees the result.

## Run termination contract

Ray evaluates trial stopping rules before calling the scheduler. The supported facade therefore accepts only one stop key: the same common monotonic progress attribute used by `ClanBasedTraining` for perturbation boundaries. Fitness thresholds, callable stoppers, independent early stopping, and wall-clock time budgets are rejected because they can remove one member while peers still require it for collective training.

## Rejected configurations in the first release

The implementation rejects or deliberately does not support:

- asynchronous PBT;
- population time-multiplexing or Ray result buffering;
- actor reuse;
- a separate Ray search algorithm or wall-clock Tune budget;
- fewer concurrent trial slots than clan members;
- independent trial retries;
- mutations outside declared optimizer fields;
- nested mutation dictionaries or custom explore functions;
- multiple resource bundles per trial;
- more than one Lightning device/process per trial;
- multiple optimizers;
- manual optimization;
- Lightning learning-rate schedulers, checkpoint callbacks, or EarlyStopping;
- SyncBatchNorm;
- DDP communication hooks, model averaging, FSDP, or DeepSpeed;
- changing world size on restore;
- checkpoint retention of two or fewer artifacts.

A mid-window member failure invalidates the collective window. The first release fails the Tune run rather than attempting independent repair.

## Verified and unverified gates

Verified locally with Lightning 2.6.5 and PyTorch 2.10.0 on two CPU/Gloo processes:

- common reduced gradients with divergent optimizer application;
- fresh-model synchronization without DDP `init_sync`;
- checkpoint creation on nonzero clan ranks;
- source checkpoint restoration into multiple trials;
- inherited optimizer momentum;
- post-restore target learning-rate mutation;
- process-group destruction and reformation.

Still requires the Ray-enabled CI contract:

- full native Tune population residency;
- named-actor rendezvous from separate Tune trial actors;
- one complete synchronous PBT exploit cycle;
- actor pause/recreation and checkpoint delivery;
- process-group reformation after exploit;
- Tune experiment restoration.

The package metadata is intentionally limited to the reviewed minor versions until this compatibility suite is broadened.
