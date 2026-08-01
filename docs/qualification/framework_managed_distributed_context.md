# Framework-managed distributed-context qualification

Status: accepted qualification boundary

## Purpose

This document states what the initial Tune-trial-to-Lightning/PyTorch distributed path
must prove before the project claims that one trial can operate as one Clan member in a
shared DDP group.

This is an evidence boundary, not architecture. An untested topology is unsupported; it
is not automatically prohibited.

## Required qualification path

The initial path must be exercised with:

- real Ray Tune trials rather than stand-alone test actors;
- at least two concurrently live stable Clan members;
- one externally launched Lightning training process per trial;
- one native PyTorch DDP group spanning those member processes; and
- population fitness exchanged through that already-established distributed context.

A controller callback, mocked strategy, isolated Ray collective, or manually created
GLOO process group is not evidence for this topology.

## Cohort admission evidence

Tests or a retained executable harness prove that:

- the complete configured Clan can be admitted with its required resources;
- no partial cohort holds resources indefinitely while preventing the remaining members
  from being scheduled;
- every admitted trial belongs to exactly one active Clan cohort; and
- no trial enters distributed initialization under mixed generation or cohort metadata.

The evidence records the exact Ray mechanism used for resource reservation, placement,
and trial release. It must show that Tune remains the native trial and resource owner.

## Identity and topology evidence

Tests prove that:

- one live Tune trial maps to one stable Clan member;
- one member process maps to one DDP rank for the initial path;
- every required member and rank appears exactly once;
- stable member identity remains correctly associated with rank-derived collective
  results; and
- rank ordering or trial scheduling order is not mistaken for undocumented identity.

The first implementation may assign the same integer to member identity and rank, but the
evidence must establish that assignment rather than rely on incidental ordering.

## Framework-ownership evidence

Source inspection and executable behavior prove that:

- Ray Tune creates and resources the trial processes;
- ClanBasedTuning supplies only Clan cohort and topology metadata;
- Lightning/PyTorch initialize and own the distributed group;
- the qualified framework or external trial-process lifecycle releases the group;
- backend and device behavior come from the qualified Lightning/PyTorch path; and
- production ClanBasedTuning code does not call Ray collective-group construction,
  `torch.distributed.init_process_group`, `torch.distributed.destroy_process_group`, or
  equivalent backend lifecycle APIs.

A test harness may configure the framework path, but the production population component
must not own process-group creation or release.

## Shared-training evidence

The initial DDP qualification proves that:

- every required member contributes to one common reduced gradient;
- corresponding supported parameters receive the same reduced gradient before local
  optimizer application;
- member-local optimizer configurations can produce divergent parameter updates after
  that common gradient; and
- no later DDP synchronization silently erases the intended member divergence.

This evidence may begin with a minimal model and optimizer. It does not by itself qualify
the full Lightning training, checkpoint, or scheduler lifecycle.

## Population-resolution evidence

At a qualifying boundary, tests prove that:

- each member contributes exactly one finite local fitness through the established group;
- every successful member receives complete fitness associated with stable member
  identity;
- minimizing, maximizing, and stable tie behavior agree across workers;
- payload conversion does not change the selected member for supported values;
- the first controller query performs one exchange; and
- repeated queries use the cached result without another collective operation.

The exact collective call and payload representation are recorded as implementation
evidence, not elevated into architecture.

## Lifecycle and failure evidence

The real framework path exercises at least:

- incomplete cohort admission;
- a member that fails before distributed initialization;
- a member that fails while peers are in distributed work;
- a member that never reaches the population boundary; and
- malformed or non-finite local fitness.

Each case demonstrates that:

- no checkpoint source is accepted from a partial population;
- no next generation is released;
- peers fail or are released through supported Ray, Lightning, and PyTorch lifecycle
  behavior rather than a package-owned communication watchdog; and
- the experiment does not continue with a silently reduced Clan.

The exact timeout, cancellation, and process-group release behavior may differ by
qualified framework path. The evidence must state how the common failure outcome and
resource release are achieved.

## Checkpoint and scheduler evidence

Later complete-integration evidence proves that:

- exactly the worker selected through population resolution retains and reports the
  checkpoint;
- the CBT Tune scheduler independently selects the same member from reported results;
- a missing, extra, or losing checkpoint is rejected;
- producer provenance matches the selected member and active controlled optimizer
  configuration; and
- every next-generation member receives the same accepted continuation.

Those claims are not established merely by qualifying the distributed context.

## Initial non-claims

Unless separately qualified, the initial path does not claim support for:

- elastic membership or world-size changes;
- model sharding or ClanFSDP;
- multiple distributed processes inside one Clan member;
- multiple Clan cohorts sharing one distributed group;
- mixed CPU and CUDA membership in one group;
- arbitrary Lightning strategies or third-party backends; or
- recovery that resumes the same failed distributed operation.

These are qualification limits, not architectural prohibitions.

## Evidence record

Every implementation change that establishes or broadens support records:

- exact Ray, Lightning, PyTorch, and Python versions;
- device and backend observed for each path;
- member count and resource assignment;
- trial, stable-member, rank, and device mapping;
- cohort-admission and rendezvous mechanism;
- collective operation and payload representation;
- process-group lifetime and release mechanism;
- timeout and failure configuration;
- commands or retained harness used;
- pass/fail output; and
- any support claim intentionally withheld.
