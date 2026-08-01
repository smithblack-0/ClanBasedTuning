# System behavioral contracts

Status: active Milestone 3 behavioral contract

These contracts describe observable training outcomes. Unit and framework tests may protect individual mechanisms, but milestone acceptance must exercise the supported Tune and Lightning path.

## 1. Common continuation

At the beginning of each generation, every member restores the selected parent's model state, optimizer history, and training-progress state. No losing continuation survives.

Member genomes may differ only because the scheduler assigns one target genome per trial after restoration.

## 2. Genome application preserves inherited state

The current target genome is applied after checkpoint restoration. Applying it changes only declared optimizer fields and does not recreate the optimizer, clear optimizer history, alter model state, or advance training progress.

The shared checkpoint is not pre-mutated for one receiver's child role.

## 3. Producer provenance matches the applied genome

The worker controller owns an independent copy of the current assigned genome. Mutation of the caller's original mapping cannot change that copy.

The copied values equal the controlled values applied to the optimizer. The controller records them only if that worker is selected; it does not apply or mutate them.

## 4. Shared gradients and local optimizer behavior

Every active member contributes to the PyTorch DDP gradient reduction. Corresponding parameters receive the same reduced gradient before the local optimizer step.

Optimizer history and controlled values remain local. Starting from equal training state and receiving the same gradient, different valid genomes must produce the expected member divergence. Later DDP activity must not erase that intended divergence.

## 5. Comparable local fitness

Every member is evaluated at the same logical training boundary on an equivalent held-out workload with the same metric definition.

Fitness is computed from the reporting member's local model state and remains member-local until CBT compares the population. Distributed metric reduction must not collapse distinct candidate fitness values.

## 6. Exactly one selected continuation

For a complete generation with one selected member:

- exactly one persistent checkpoint is reported;
- its payload matches that member's model, optimizer history, and training progress;
- its producer metadata contains only schema version, stable member ID, and copied current genome;
- the metadata matches the scheduler-selected member and active trial configuration; and
- every next member restores that same checkpoint.

No losing state is loaded, averaged, or mixed into the next generation.

## 7. Incomplete artifacts are not published

If winner-side producer annotation fails after checkpoint construction but before reporting, the checkpoint is not reported, the scheduler does not accept it, and no next member begins.

## 8. A partial population cannot advance

If any required member fails, omits fitness, duplicates participation, contributes malformed data, or reaches the wrong generation boundary:

- no checkpoint source is accepted;
- no member begins the next generation;
- the Clan does not silently shrink; and
- waiting work is released through a surfaced failure.

## 9. Scheduler transition is all-or-nothing

No target begins the next generation until winner verification, producer-metadata verification, child-genome derivation, scheduler persistence, target configuration installation, and common checkpoint assignment are complete for every target.

Recovery restores the last completed transition or fails the experiment. Mutation state and lineage cannot advance independently of the assignments released to workers.

## 10. The lifecycle repeats

At least two consecutive generation transitions must demonstrate:

- common restoration;
- post-restore child-genome application;
- shared gradients;
- optimizer-driven divergence;
- comparable local fitness;
- one correctly annotated selected checkpoint; and
- scheduler-controlled continuation into the following generation.

A one-off transfer is insufficient.

## 11. Deterministic transition under accepted deterministic inputs

Given the same completed candidate states, active genomes, fitness reports, experiment seed, and supported deterministic framework settings, the transition produces the same selected continuation, producer metadata, child genomes, scheduler mutation state, and first deterministic update of the next generation.

## Evidence rule

The complete evidence set must include a real multi-member Ray Tune and Lightning DDP workflow. Focused tests may inspect controller state, Ray membership, checkpoint metadata, scheduler persistence, and framework callbacks, but those assertions do not replace the observable training outcomes above.

Hardware, backend, and topology support may be claimed only where the corresponding path has direct qualification evidence.
