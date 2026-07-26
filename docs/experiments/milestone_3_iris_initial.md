# Milestone 3 initial Iris experiment

Status: first qualifying integrated scientific workload  
Run date: 2026-07-26  
Implementation: `examples/iris_clan_experiment.py`  
Evidence run: GitHub Actions run 601, Python 3.11 Ray contract job

## Question

Can the public manual Milestone 3 path execute a real classification workload, adapt an
optimizer policy over repeated rounds, preserve the required Clan lifecycle, and emit
sufficient evidence for scientific inspection?

This is not a test of whether Clan Tuning outperforms a known schedule or ordinary PBT.
The workload is intentionally small and serves as the first integrated scientific use
of the product.

## Dataset

The experiment uses Fisher's Iris classification dataset through
`sklearn.datasets.load_iris`:

- 150 plant samples;
- four continuous measurements;
- three species classes;
- deterministic stratified split of 120 training and 30 validation samples;
- standardization fitted on the training split.

Dataset citation: Fisher, R. A. (1936), *Iris*, UCI Machine Learning Repository,
DOI `10.24432/C56C76`. The UCI distribution is CC BY 4.0.

## Model and training

- model: `Linear(4, 16) → Tanh → Linear(16, 3)`;
- loss and fitness: validation cross-entropy, minimized;
- optimizer: SGD with momentum 0.9;
- population: two concurrently resident CPU members;
- distributed backend: Gloo;
- training data: ordinary DDP partitioning;
- validation data: identical replicated held-out set;
- controlled optimizer value: learning rate;
- initial learning rates: 0.01 and 0.12;
- mutation: linear Gaussian displacement, standard deviation 0.025, clamped to
  `[0.002, 0.2]`;
- reports per trial: five;
- completed sole-parent transitions: four;
- actor reuse: disabled;
- independent trial recovery: disabled.

## Result

The qualifying run completed without member errors in 39.19 seconds with two concurrent
CPU allocations.

| Member | Final learning rate | Validation loss | Validation accuracy |
| --- | ---: | ---: | ---: |
| 0 | 0.09673695 | 0.11733710 | 0.96666664 |
| 1 | 0.12000000 | 0.11304882 | 0.96666664 |

The selected path was:

| Completed round | Winner member | Winning learning rate |
| ---: | ---: | ---: |
| 0 | 1 | 0.12 |
| 1 | 1 | 0.12 |
| 2 | 1 | 0.12 |
| 3 | 1 | 0.12 |

Each transition used one controller-selected winner checkpoint. The next population
restored from that parent and then applied member-local learning-rate configurations.

## Interpretation

The run establishes the intended scientific capability:

- a real labeled classification dataset passes through the public integrated path;
- the live population completes repeated shared-gradient rounds;
- one optimizer-policy lineage is selected and inherited;
- loser configurations continue to explore around the common parent;
- metrics, elapsed cost, selected lineage, and limitations are available for review.

The result does **not** show that Clan Tuning improved Iris performance. Both final
members reached the same validation accuracy, the lower-loss difference was small, and
the higher initial learning-rate member won every round. This may simply reflect that
0.12 was already a strong schedule for this short, easy task.

## Limitations

- Iris is extremely small and easy and cannot establish broad optimizer-policy value.
- The population has only two members and tunes only learning rate.
- There is no fixed-schedule, learning-rate-scheduler, or ordinary-PBT comparison.
- One run does not measure variance across seeds or splits.
- CPU/Gloo evidence does not qualify GPU, multi-node, or sharded execution.
- The test measures integrated scientific usability, not cost competitiveness.

## Next scientific step

A later experiment should use a task with a longer useful optimization trajectory and
compare Clan Tuning against at least a fixed schedule and an ordinary scheduler under
reported compute budgets. That expansion should follow product capability rather than
inflate the Milestone 3 support claim.
