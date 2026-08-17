# Performance qualification

Status: reproducible measurement harness; representative evidence not yet recorded.

Performance is not inferred from unit-test speed. ClanBasedTuning adds generation-boundary
coordination, checkpoint construction/persistence, Tune pause/resume, and function-process
restart/restore work around ordinary model training. The relevant question is how large that
cost is relative to useful training rounds on intended hardware.

## Tiny measurement harness

From a development checkout:

```bash
python benchmarks/tiny_function_path.py --generations 3
```

The script runs the real two-member CPU function path with the tiny MLP/AdamW workload and
prints JSON containing:

- total wall-clock time;
- population size and requested generation count;
- final Tune training iteration for each member;
- Ray member `time_total_s`;
- retained checkpoint count and total bytes; and
- final validation losses.

The workload has no external download and is intended to make framework/control-plane costs
visible. It is not representative model throughput by itself.

## Evidence needed for performance claims

Record measurements on the hardware/topology a claim concerns, including commit SHA,
framework versions, CPU/GPU model, population size, round length, model/workload description,
and storage type. For useful training workloads also record examples/tokens/samples per
second or another domain-relevant throughput measure with and without CBT where a meaningful
comparison exists.

Do not derive a universal pass/fail number from GitHub-hosted CI. In particular, actor reuse
or a more complex execution API should be reconsidered only if representative measurements
show restart/restore overhead is material relative to the intended round duration. Complexity
is not earned merely because the tiny benchmark is intentionally overhead-heavy.
