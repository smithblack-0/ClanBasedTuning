# Tiny function-path benchmark

This benchmark measures the real Ray Tune + Lightning Clan function path without downloading
a model or dataset. It uses the same two-layer MLP/AdamW workload as the realistic framework
contracts and reports wall-clock time, Ray member time, checkpoint bytes, and completed
training iterations.

Run it from a development checkout:

```bash
python -m pip install -e '.[dev]'
python benchmarks/tiny_function_path.py --generations 3
```

The output is measurement data, not a pass/fail threshold. Record results from representative
hardware before using them to justify actor reuse, a different public API, or a performance
support claim. CPU CI timing is useful for regression diagnosis but is not representative
training-performance evidence.
