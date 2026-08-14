# Population-resolution invariants

Status: accepted architectural contract

## Population boundary

1. One live Tune trial represents one stable Clan member.
2. A successful generation boundary contains exactly one report from every configured member.
3. Every report belongs to the same Tune progress boundary.
4. Every fitness remains associated with its stable member and is finite/comparable.
5. Candidate fitness remains member-local until the Clan population exchange.
6. A missing, duplicated, malformed, failed, or cross-generation member cannot be
   reinterpreted as a smaller valid Clan.

The initial DDP path uses the already-established Lightning/PyTorch group to exchange fitness;
population resolution creates no second process group or backend lifecycle.

## Selection

A successful boundary identifies exactly one selected member. Comparison direction and stable
tie behavior belong to the shared framework-independent selection implementation. Worker-side
selection and scheduler-side verification use the same rule.

Exactly one member may report the persistent Clan continuation checkpoint. The scheduler
independently verifies that the declared checkpoint source equals its selected member.

## Next generation

Every next member receives:

- the same selected training continuation; and
- its own independently mutated genome derived from one snapshot of the selected parent's
  current Tune config.

The prior winner is also a target and receives a mutation. No child mutation may use another
already-mutated child as its parent. Seeded mutation assignment is stable with respect to
member identity rather than incidental framework iteration order.

Genome application remains userspace. These invariants determine which config CBT supplies,
not what user code does with it.

## Runtime isolation

Stable member assignment is scheduler-owned. Internal runtime discovery may choose any
representation that preserves experiment/trial identity unambiguously. Concurrent Tune
experiments with equal trial IDs must not collide.

Each independently launched function invocation joins one complete rendezvous session using
fresh invocation identity. Mixed old/new invocation members may not form a valid DDP cohort.

## Failure

An invalid boundary must not intentionally:

- choose from a partial population;
- silently shrink the Clan;
- accept a losing checkpoint as continuation; or
- release a deliberately mixed next generation.

Unsupported failure modes may fail the experiment rather than recover. Bounded recovery after
a participant disappears inside an active framework collective is not implied by the
pre-DDP rendezvous timeout.

## Representation freedom

The implementation may change internal container types, helper names, actor layout, timeout
mechanisms, or exact framework hooks while these invariants remain mechanically established.
Stable member ID currently equals DDP global rank by deliberate initial-topology design; a
future model-sharded/multi-node topology may introduce additional dimensions without changing
the population semantics above.
