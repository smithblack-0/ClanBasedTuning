# System behavior

Status: accepted behavioral contract

## 1. One common inherited continuation

At the beginning of a generation every member receives the selected parent's model state,
optimizer history, and training progress. No losing continuation is averaged, merged, or
mixed into the next generation.

Every receiving member also receives its own current Tune config/genome. CBT supplies that
config but does not interpret or apply it. User code may explicitly change optimizer-side
policy after Lightning has restored inherited state.

## 2. Shared training with member-local post-gradient variation

Every required member contributes its local training work to the common DDP gradient. The
corresponding trainable parameters receive the same reduced gradient before each member
performs its local optimizer update.

Valid Clan variation is applied after that common gradient has been computed. Different
optimizer-side policy may therefore produce intended member divergence without changing the
training problem whose gradients were pooled.

Later framework synchronization must not silently erase that divergence.

## 3. Comparable member-local fitness

Every member is evaluated at the same logical training boundary on an equivalent held-out
workload using the same metric definition. Candidate fitness remains associated with that
member until population comparison; distributed metric reduction must not collapse distinct
candidate values before selection.

A concrete data-loading support claim must establish comparable evaluation workloads rather
than merely simultaneous validation timing.

## 4. One selected continuation

A valid generation selects exactly one stable member. The continuation used by every next
member must match that selected candidate's model state, optimizer history, and Lightning
training progress at the evaluated boundary.

Only the selected member may report the persistent Clan continuation checkpoint. The Tune
scheduler independently verifies worker winner/checkpoint-source claims before accepting the
transition.

## 5. Complete sibling next generation

Every next member, including the preceding winner, receives:

- the same selected training continuation; and
- an independently mutated genome derived from one snapshot of the selected parent's genome.

Children are siblings, not a mutation chain. A seeded generation assigns mutations in stable
member-ID order so incidental framework iteration order cannot change the result.

Genome application remains userspace and is not part of the scheduler transition.

## 6. Complete population participation

A generation is valid only for the complete configured Clan. Missing, duplicated, malformed,
failed, or cross-generation participation cannot be reinterpreted as a smaller valid
population.

The scheduler must not knowingly release a generation containing mixed checkpoints, parent
states, or boundary identities.

## 7. Repeated operation and restoration

The supported integration must complete successive generations through the same public path.
One-off policy tests or isolated state transfer are insufficient evidence.

When interrupted-experiment restoration is claimed, the same ordinary Tune function path
must resume through `Tuner.restore` with scheduler/runtime state reconstructed from Tune's
persisted experiment rather than a second CBT recovery API.

## Evidence boundary

Focused unit tests may establish individual algorithms and state machines. Acceptance of a
complete support path requires a real multi-member Ray Tune + Lightning/PyTorch run observing
the behaviors above across repeated generations.

Backend, device, topology, framework version, checkpoint plugin, recovery, and scale claims
require direct evidence for the path claimed. Dependency metadata indicates installability,
not automatic qualification.
