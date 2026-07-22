# Native Tune-trial execution seam: CPU contract probe

Status: actual package `ClanDDPStrategy` verified; native Ray Tune/PBT lifecycle covered by a separate Ray-required test

Date: 2026-07-21

## Question

Can independently managed trial processes use the package strategy to join one shared-gradient process group, preserve separate optimizer trajectories, checkpoint every trial, restore a target from a source checkpoint, apply a mutated optimizer config after restore, and reform the group?

## Probe

Two CPU processes stand in for separately launched Tune trial actors. Each creates its own Lightning `Trainer`, model, optimizer configuration, and checkpoint path. The probe uses the real `ClanDDPStrategy` with a supplied `ClanRuntime` and Gloo backend.

### Window 1

The processes construct weights `1.0` and `3.0`. Because this is a fresh population, the strategy explicitly synchronizes both to rank 0's weight `1.0` before DDP wrapping. It then disables further parameter/buffer initialization synchronization.

Both members receive reduced gradient `2.0` and apply different learning rates:

| Trial | Learning rate | Final weight | Momentum |
|---|---:|---:|---:|
| rank 0 | 0.1 | 0.8 | 2.0 |
| rank 1 | 0.2 | 0.6 | 2.0 |

Both trial-local checkpoints are written, including rank 1's checkpoint.

### Exploit-style transition

Both processes are terminated and recreated with a new process-group endpoint. Both restore rank 0's checkpoint, simulating PBT assigning one source checkpoint to a retained source and an exploited target.

State observed after restore:

| Trial | Global step | Weight | Momentum | Applied learning rate |
|---|---:|---:|---:|---:|
| rank 0 | 1 | 0.8 | 2.0 | 0.1 |
| rank 1 | 1 | 0.8 | 2.0 | 0.3 |

The target inherits complete optimizer momentum and then receives its mutated trial configuration.

### Window 2

The reformed group produces reduced gradient `1.6` and momentum `3.4` on both members. Different current learning rates then produce final weights `0.46` and `-0.22`.

## Conclusion

The Lightning/DDP responsibility is viable:

- explicit fresh synchronization replaces destructive DDP `init_sync`;
- ordinary DDP supplies the common gradient;
- optimizer application remains trial-local;
- every native trial can own a complete Lightning checkpoint;
- source checkpoint inheritance and target optimizer mutation occur in the correct order;
- independently recreated processes can form the next group.

The Ray-required regression test under `tests/framework_contracts/test_ray_native_pbt_cycle.py` covers the remaining scheduler/rendezvous boundary and is executed when Ray is installed.
