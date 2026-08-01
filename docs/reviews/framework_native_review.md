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
optimizer-side variation, comparable fitness, and one selected continuation.

Fail the review when engineering convenience changes one of those properties. That is a
product or contract change, not a local implementation choice.

## 2. Use the native owner

Trace each responsibility to PyTorch, Lightning, Ray Tune, ClanBasedTuning, or the user
application. Use the framework owner unchanged when its contract already fits.

Fail when ClanBasedTuning repeats ordinary scheduling, training, validation,
distribution, checkpoint, optimizer, data, resource, or lifecycle behavior merely for
local convenience.

## 3. Require a demonstrated framework gap

Custom behavior requires a concrete statement of:

- the Clan behavior required;
- the native behavior that conflicts with or omits it;
- the smallest seam capable of bridging the difference; and
- the evidence showing that ordinary composition is insufficient.

Speculative generality, symmetry, or preference for local control is not a framework
gap.

## 4. Keep one authority and a narrow seam

The custom seam adds only the missing Clan behavior. Policy, state, and execution each
have one authoritative owner. Removing the seam should remove the Clan-specific behavior
without taking an ordinary framework lifecycle with it.

Fail when responsibilities overlap, configuration is mirrored without need, or custom
machinery mainly exists to coordinate other custom machinery.

## 5. Match support to evidence

Every version-sensitive, distributed, persistence, recovery, performance, device, or
failure claim identifies direct source evidence or an executable qualification and the
support envelope it establishes.

Return **insufficient evidence** when the boundary is plausible but the claim is not yet
established. Narrow the claim rather than freezing an implementation or inferring support
from a neighboring path.

## Result

- **Pass:** all checks hold for the claimed behavior and support envelope.
- **Fail:** the unit changes Clan meaning, duplicates a native owner, or creates
  conflicting authority.
- **Insufficient evidence:** the boundary may be correct, but the support claim has not
  been qualified.

## Governing references

- [Product roadmap](../product_roadmap.md)
- [Current integration design](../design/integration.md)
- [System behavioral contract](../contracts/system_behavior.md)
- [Population-resolution invariants](../contracts/population_resolution_invariants.md)
- [Population-resolution responsibilities](../contracts/population_resolution_responsibilities.md)
- [Current implementation plan](../plan.md)
