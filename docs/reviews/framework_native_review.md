# Framework-native engineering review

Status: standing go/no-go review

## Purpose

Use this review whenever a design or implementation changes a meaningful
ClanBasedTuning framework boundary. It asks:

> Does this unit preserve the Clan mechanism while leaving ordinary framework behavior
> with its native owner?

The roadmap and accepted contracts define the required behavior. This review does not
create new product requirements or choose an implementation before evidence exists.

## 1. Preserve the Clan mechanism

Confirm that the unit preserves complete-population cooperation, common gradients,
member-side variation, comparable fitness, one selected continuation, and sibling
next-generation mutations from that selected parent.

Fail the review when engineering convenience changes one of those properties. That is a
product or contract change, not a local implementation choice.

## 2. Use the native owner

Trace each responsibility to PyTorch, Lightning, Ray Tune, ClanBasedTuning, or the user
application. Use the framework or user owner unchanged when its contract already fits.

Fail when ClanBasedTuning repeats ordinary scheduling, training, validation,
distribution, checkpoint, optimizer, data, resource, or lifecycle behavior merely for
local convenience.

## 3. Preserve userspace genome ownership

Trace the genome all the way from Tune config assignment into the user's function.

Pass only when:

- CBT may select or mutate config values but does not define what their keys mean;
- the user's function receives the ordinary current genome/config;
- user code alone decides how that genome affects optimizer, model, or other state; and
- tests that demonstrate application keep the application logic in test/userspace code.

Fail immediately if production CBT introduces any of the following without an explicit
product-contract change:

- an `apply_genome` abstraction owned or invoked by CBT;
- inferred mapping from genome keys to optimizer fields;
- optimizer-param-group inspection for genome application;
- a restore callback whose purpose is to apply the genome;
- a Lightning post-load hook that applies the genome; or
- a convenience API that hides application while claiming the user still owns it.

A genome commonly representing optimizer hyperparameters does not transfer optimizer
application ownership to CBT.

## 4. Require a demonstrated framework gap

Custom behavior requires a concrete statement of:

- the Clan behavior required;
- the native behavior that conflicts with or omits it;
- the smallest seam capable of bridging the difference; and
- the evidence showing that ordinary composition is insufficient.

Speculative generality, symmetry, or preference for local control is not a framework
gap.

## 5. Keep one authority and a narrow seam

The custom seam adds only the missing Clan behavior. Policy, state, and execution each
have one authoritative owner. Removing the seam should remove the Clan-specific behavior
without taking an ordinary framework lifecycle with it.

Fail when responsibilities overlap, configuration is mirrored without need, or custom
machinery mainly exists to coordinate other custom machinery.

## 6. Match support to evidence

Every version-sensitive, distributed, persistence, recovery, performance, device, or
failure claim identifies direct source evidence or an executable qualification and the
support envelope it establishes.

Return **insufficient evidence** when the boundary is plausible but the claim is not yet
established. Narrow the claim rather than freezing an implementation or inferring support
from a neighboring path.

## Result

- **Pass:** all checks hold for the claimed behavior and support envelope.
- **Fail:** the unit changes Clan meaning, duplicates a native/user owner, or creates
  conflicting authority.
- **Insufficient evidence:** the boundary may be correct, but the support claim has not
  been qualified.

## Governing references

- [Product roadmap](../product_roadmap.md)
- [Current integration design](../design/integration.md)
- [System behavioral contract](../contracts/system_behavior.md)
- [Population-resolution invariants](../contracts/population_resolution_invariants.md)
- [Population-resolution responsibilities](../contracts/population_resolution_responsibilities.md)
- [Public API](../api.md)
- [Current implementation plan](../plan.md)
