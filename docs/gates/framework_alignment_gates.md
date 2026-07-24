# Framework-alignment invariant gates

Status: proposed milestone-one gates for human acceptance  
Date: 2026-07-24

These gates state what subsequent design and implementation must not violate.
The research report explains the evidence and tradeoffs behind them.

## Algorithm gates

1. One Ray Tune trial is one Clan member.
2. Every live member participates in every pooled training gradient.
3. All members begin each round from one inherited model state and optimizer
   state, then apply member-local optimizer configuration.
4. Every completed nonterminal round selects exactly one parent.
5. The selected parent's model parameters, optimizer state, and optimizer
   configuration are the sole basis of the next generation.
6. Only optimizer-side configuration may vary between members during a round.
   Model, data, and other gradient-defining configuration may not be mutated.

## Round and evaluation gates

7. A round boundary is a qualifying Lightning-owned evaluation-and-checkpoint
   event.
8. ClanBasedTuning may not introduce a second validation cadence, round clock,
   epoch counter, optimizer-step conversion, or batch counter to define that
   boundary.
9. Ray PBT receives exactly one evolutionary report per qualifying evaluation
   event. Sanity checks and unrelated reports may not trigger evolution.
10. Every member evaluates the same held-out examples in the same deterministic
    order and produces one member-local fitness value.
11. Fitness may not be synchronized across DDP ranks before population
    comparison.
12. Supported evaluation cadence must cause every member to enter validation at
    the same training-loop location. A cadence is unsupported until that property
    and checkpoint continuation are tested.

## Population and resource gates

13. Ray `TuneConfig.num_samples` is the initial Clan population input. A
    separate package population size is not permitted.
14. Initial support uses Ray's default variant generator without grid expansion
    or another search algorithm. The generated trial count must equal
    `num_samples`.
15. Ray `num_samples`, `max_concurrent_trials`, generated trials, Clan members,
    DDP world size, and concurrently resident dedicated devices must be equal.
16. The complete population must be simultaneously resident before training.
    Queuing, time multiplexing, actor reuse, and partial-population execution are
    unsupported.
17. Initial support uses one complete model replica and one device per trial.
18. Full-residency validation must occur at an assembly boundary capable of
    seeing the Tune population, concurrency, resource request, and cluster
    allocation before any member enters DDP.

## Framework-ownership gates

19. Ray Tune owns trial identity, trial configuration, synchronous population
    scheduling, checkpoint selection and transfer, pause, and resume.
20. Lightning owns training and validation loops, validation cadence, checkpoint
    contents, restoration, optimizer construction, and dataloader integration.
21. PyTorch DDP owns gradient collectives and native distributed wrapper behavior
    wherever a qualified public or version-pinned seam fits.
22. ClanBasedTuning may add only behavior required by the Clan mechanism or by a
    demonstrated framework gap. It may not introduce a second training loop,
    Tune configuration language, checkpoint scheduler, optimizer factory,
    validation scheduler, or data system.
23. Existing proof-of-concept classes and file boundaries have no architectural
    presumption. Reuse requires satisfaction of these gates.

## Evolutionary-controller gates

24. The initial controller is synchronous.
25. Selection uses one deterministic winner and targets every other live member.
26. Tie handling, elite behavior, invalid fitness, and mutation scope are
    explicit, deterministic contracts.
27. The controller does not own training, validation cadence, DDP collectives,
    optimizer construction, checkpoint contents, or dataloaders.
28. A private upstream seam requires a pinned dependency range, an explanatory
    comment, and an executable framework-contract test.

## Checkpoint and optimizer gates

29. Every member must be able to produce a trial-local Lightning checkpoint at a
    qualifying evaluation boundary.
30. Ray's native PBT exploitation path remains authoritative for source
    checkpoint selection and transfer.
31. Lightning restores inherited model and optimizer state through its normal
    checkpoint lifecycle.
32. The receiving trial's current optimizer configuration is applied after
    inherited optimizer-state restoration.
33. Optimizer configuration application is explicit and may not silently ignore
    missing or unsupported fields in a supported binding.
34. Independently acting LR schedulers or other optimizer-hyperparameter owners
    are unsupported until one combined authority is designed and tested.
35. Whole-experiment restoration across an interrupted round is not an initial
    support claim.

## DDP and precision gates

36. Corresponding members must have compatible model, parameter, buffer,
    optimizer-class, and parameter-group topology.
37. DDP may synchronize the common initial state but may not broadcast member
    buffers during divergent training.
38. Standard gradient reduction remains framework-owned; custom communication,
    skipped reduction, model averaging, SyncBatchNorm, and manual optimization
    are unsupported until separately qualified.
39. Precision modes are supported only after divergent-member contract probes.
    No precision mode is accepted or rejected solely by analogy to ordinary DDP.

## Failure and stopping gates

40. One active member failure invalidates the active clan.
41. Initial behavior is collective failure or stop, not independent member
    recovery, world-size shrinkage, or speculative repair.
42. Per-trial Tune stopping and member-local Lightning early stopping are
    unsupported.
43. Planned completion occurs only at a synchronized population boundary and
    stops the complete clan.
44. External cancellation or hard global interruption may stop the complete clan
    without another evolutionary transition.

## Gate maintenance

A later design may revise a gate only when new evidence is recorded in the
research ledger and the change is accepted as an explicit project decision.
Implementation difficulty alone is not evidence that a gate is wrong.
