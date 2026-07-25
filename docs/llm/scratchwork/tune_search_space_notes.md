# Tune search-space observations for later CBT integration

Status: preliminary, non-authoritative, and disposable

These notes preserve framework context discovered while designing the independent
controller. They do not select the Milestone 3 integration seam or establish a public
API.

## Observations

- Tune parameter domains carry bounds and a sampler such as uniform or log-uniform.
- The geometry matters to CBT mutation: ordinary uniform-style coordinates imply
  additive movement, while log coordinates imply multiplicative movement in the
  original value.
- Ordinary PBT uses `hyperparam_mutations` as a resampling or perturbation source.
  Complete resampling is not obviously appropriate for CBT because a large optimizer
  jump may be incompatible with the inherited model trajectory and shared-gradient
  regime.
- CBT needs a required viable starting value in addition to local perturbation scale,
  geometry, and bounds.
- A possible future Tune-facing declaration is a Tune-compatible float domain carrying
  required default and deviation metadata, exposed through helpers resembling
  `cbt.uniform(...)` and `cbt.loguniform(...)`.
- Whether Tune preserves such domain objects long enough for the scheduler to inspect,
  or whether an earlier orchestration layer must translate them, remains an integration
  question.

## Milestone 2 translation

The independent `ClanController` does not consume Tune objects. Its accepted internal
policy mapping carries only the information required for calculation:

```python
{
    "lr": {
        "default": 3e-4,
        "std": 0.25,
        "sampling": "log",
        "lower": 1e-5,
        "upper": 1e-2,
    }
}
```

This keeps the evolutionary calculation directly testable. It does not decide how a
future Ray-native user declaration is constructed, preserved, or translated.
