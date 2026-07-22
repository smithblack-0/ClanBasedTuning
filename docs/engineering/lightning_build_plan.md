# Lightning integration build and verification plan

Status: superseded build plan for the one-outer-job design. Retained for comparison; the current native Tune-trial design is defined in [`native_trial_build_contract.md`](native_trial_build_contract.md).

Date: 2026-07-21

## 11. Proposed package boundaries

The exact file layout should remain adjustable during implementation, but the contracts imply roughly:

```text
clan_based_tuning/
    scheduler.py          # snapshots, plans, scheduler protocol/default policy
    mutations.py          # explicit mutation domains and operations
    optimizer.py          # optimizer bindings and genome application
    transfer.py           # framework-independent tensor-tree transfer primitives
    lineage.py            # generation event and replay representation

    lightning/
        strategy.py       # ClanDDPStrategy
        callback.py       # ClanTuningCallback
        fitness.py        # replicated sampler and reporter
        checkpoint.py     # manifest/shard format and callback
        facade.py         # small user-facing setup helper

    ray/
        strategy.py       # optional RayClanDDPStrategy
        callback.py       # optional Ray checkpoint/report adapter

examples/
    raw_ddp_reference.py
    lightning_minimal.py
    ray_lightning.py
```

Do not create every file before its contract is exercised. The list is a responsibility map, not a mandate to produce empty abstractions.

## 12. Build sequence

### Stage 1 — domain policy and transition records

Implement and test:

- immutable member snapshots;
- generation plans;
- deterministic scheduler initialization;
- champion selection;
- mutation domains;
- elite retention;
- scheduler state serialization;
- lineage JSONL/replay representation.

No Lightning imports in this layer.

### Stage 2 — optimizer bindings

Implement:

- param-group scalar binding;
- tuple-element binding;
- group selector;
- value capture and exact application;
- validation that every rank has identical optimizer topology;
- AdamW and SGD contract tests.

### Stage 3 — raw DDP reference and state transfer

Implement:

- common-gradient/divergent-step reference;
- source-rank parameter and buffer transfer;
- generic optimizer state transfer;
- transfer checksum tests;
- fixed-world-size assumptions;
- failure-on-structure-mismatch behavior.

This becomes the behavioral oracle.

### Stage 4 — Lightning strategy

Implement:

- DDP option enforcement;
- live transfer methods;
- delayed checkpoint restore;
- rank-sharded checkpoint save/load;
- manifest commit ordering;
- two-rank CPU integration tests.

### Stage 5 — Lightning callback and fitness path

Implement:

- `on_train_start` initialization/restore;
- generation-step tracking;
- replicated fitness sampler/reporter;
- rank-0 scheduler execution;
- plan broadcast;
- transition transaction;
- generation logging;
- dedicated clan checkpoint callback.

### Stage 6 — GPU and precision verification

Verify:

- NCCL state transfer;
- AdamW state sizes and transfer cost;
- BF16;
- gradient accumulation alignment;
- buffer-bearing models;
- checkpoint failure/restart;
- generation-boundary overhead.

FP16 remains gated until scaler synchronization is designed and tested.

### Stage 7 — Ray adapter

Implement only after local Lightning semantics are stable:

- `RayClanDDPStrategy`;
- Ray environment compatibility;
- distributed checkpoint merging;
- resume through `ray.train.get_checkpoint()`;
- cluster storage documentation.

### Stage 8 — scientific harness

Build the comparative harness using the product rather than embedding product behavior in the harness:

- best-effort scheduled DDP;
- CBT;
- full PBT;
- nearest divergent-replica baseline where appropriate;
- common accounting and logging.

The harness should test the package; it should not become the hidden implementation.

## 13. Verification gates

Compilation and single-process unit tests are insufficient.

Required gates include:

1. two ranks receive identical reduced gradients;
2. different optimizer configurations produce divergent parameters;
3. registered buffers remain rank-local during training;
4. a nonzero source rank can reseed every member;
5. model and optimizer transfer reproduce source state exactly;
6. target hyperparameter mutation occurs after source optimizer-state load;
7. fitness evaluates identical examples on every rank;
8. local fitness is not averaged before scheduler input;
9. generation plan is created once and applied consistently;
10. a crash before commit leaves the previous checkpoint authoritative;
11. checkpoint resume restores divergent member model and optimizer state;
12. world-size mismatch fails clearly;
13. lineage and scheduler RNG resume deterministically;
14. Ray merges all member shards and restores them correctly;
15. unsupported configurations fail during setup, not after hours of training.

The first three Lightning CPU probes already established gates 1–4 and the essential resume mechanism for gate 11.

## 14. Remaining design decisions

These should be resolved before implementing the associated unit, not guessed inside the code:

1. **Fitness surface:** dedicated reporter versus named local metric as the default public API.
2. **Checkpoint cadence:** generation-boundary-only initial support versus arbitrary mid-generation exact checkpoints.
3. **Transfer backend:** begin with per-tensor broadcast or implement bucketed transfer immediately.
4. **Default mutation representation:** custom package domains versus simple mutation callables.
5. **Param-group semantics:** shared value, preserved ratios, or explicit genes per group as the default.
6. **Champion at final stop:** force a final evaluation/selection or return the last committed champion.
7. **Local checkpoint retention:** package-managed keep-last versus leaving retention to user/Ray.
8. **Precision support:** whether BF16 is part of the first public release or the first follow-up after GPU tests.

None of these require a custom Trainer loop.
