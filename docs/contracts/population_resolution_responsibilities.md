# Population-resolution responsibilities

Status: accepted responsibilities for the current DDP function path

## Scheduler

`ClanScheduler` owns the configured population, stable member assignment, complete Tune-side
boundary verification, selected parent authority, mutation random stream, and complete child
config assignment.

It does not own trial resources, storage infrastructure, user optimizer application, or
PyTorch distributed execution. It uses Tune's scheduler lifecycle and delegates the few
low-level checkpoint/config transfer details to one compatibility module.

## Framework-independent evolution

`evolution.py` owns finite comparison semantics, deterministic tie behavior, mutation rule
normalization, and sibling generation from one selected parent. It accepts ordinary data and
has no Ray/Lightning/checkpoint dependencies.

The Lightning callback and Tune scheduler share its selection rule; the scheduler additionally
uses its complete generation-resolution operation to produce child configs.

## Cohort/runtime

`cohort.py` owns pure trial/member assignment and per-invocation complete-session state.
`runtime.py` owns Ray actors, Tune-context lookup, polling/timeouts, host/port discovery, and
other external effects needed to materialize that state.

Runtime state contains no genome/application behavior. Registry lookup is scoped by Tune
experiment plus trial ID so independent experiments cannot collide merely because Ray reused
a trial identifier.

## Lightning and PyTorch

Lightning/PyTorch own accelerator/backend selection, process-group initialization/lifetime,
DDP model setup, gradient collectives, barriers, training/validation loops, optimizer and
training-state restoration, and checkpoint construction.

`ClanDDPStrategy` supplies only the externally assigned topology, prevents per-forward buffer
broadcast from erasing candidate divergence, distinguishes training versus comparable
Lightning-managed validation sampler behavior, and scopes one Clan round checkpoint write to
the selected rank.

The one-process-per-Tune-member environment treats each member as a logical one-process node
for Lightning rank bookkeeping. This is not physical node authority.

## Callback

`ClanTuneReportCallback` bridges one qualifying Lightning validation boundary to one Tune
report boundary. It reads one member-local metric, gathers the complete fitness vector over
the active Lightning strategy, resolves the shared winner, coordinates Lightning checkpoint
construction, and reports the winner checkpoint plus ordinary metrics.

It has no persistent population state, mutation logic, or genome-application responsibility.

## Ray compatibility adapter

`ray_compat.py` owns the unavoidable Developer/private Tune operations required to capture a
boundary checkpoint and install that checkpoint/config as another trial's continuation.
These operations are kept separate because Ray does not promise DeveloperAPI stability across
minor releases.

A compatibility repair may change this module without changing Clan policy. Dependency
metadata therefore does not point-pin one Ray minor merely to freeze upstream PBT internals.

## User code

User code owns every interpretation and application of the Tune config/genome. The primary
Lightning pattern applies it in a user-owned `on_train_start()` hook after normal checkpoint
restore. CBT must not infer optimizer mappings or hide application in a convenience callback.

Scientific validity still constrains what may vary: Clan genes must affect choices applied
after common-gradient computation.

## Failure ownership

Each layer rejects the invalid facts it can establish. Runtime rejects failed pre-DDP cohort
formation; the callback/selection layer rejects invalid fitness; the scheduler rejects
incomplete/misaligned Tune boundaries; Lightning/PyTorch surface distributed/checkpoint
failures. No layer may convert known partial participation into a valid winner.
