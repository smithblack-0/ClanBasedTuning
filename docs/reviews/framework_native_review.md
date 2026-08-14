# Framework-native review

Status: standing engineering review

Use this review whenever a change touches Ray, Lightning, PyTorch, user/application
ownership, checkpointing, resources, or distributed lifecycle.

## 1. Preserve Clan semantics

Confirm complete-population shared-gradient cooperation, member-local post-gradient
variation, comparable member-local fitness, one selected continuation, and independent
sibling mutations from one selected parent.

Fail when an implementation convenience changes scientific meaning.

## 2. Use the native owner where it wins the overall design

Trace each responsibility to Ray Tune, Lightning, PyTorch, CBT, or user code. Prefer the
native owner when its contract fits, but do not treat this as a mechanical rule: a small
owned implementation can be better than dependence on a large unstable framework subsystem
when it improves the overall correctness/maintenance/concision balance.

The current example is scheduler evolution: CBT owns its narrow synchronous transition rather
than inheriting Ray PBT internals, while Ray still owns trial execution/resources/storage and
the unavoidable low-level transfer operations remain in one compatibility adapter.

## 3. Preserve userspace genome ownership

Pass only when Tune supplies the current config to the ordinary user function and user code
alone decides what its values mean or how they modify optimizer/model/other state.

Fail if production CBT introduces an optimizer schema, config-to-optimizer inference,
`apply_genome` abstraction, package restore/application callback, or hidden post-load
application hook.

Using a user-owned Lightning lifecycle hook to apply the genome after restoration preserves
this boundary; the operation is still user code.

## 4. Demand a demonstrated framework gap for custom machinery

For each adapter/custom component, state:

- what Clan behavior the frameworks cannot supply directly;
- what existing lifecycle remains framework-owned;
- why the chosen seam is preferable to the realistic alternatives; and
- what evidence covers the version-sensitive behavior.

Do not add generic infrastructure merely for symmetry or local control.

## 5. Concentrate unstable dependencies

A private/Developer framework operation is not automatically rejected. Compare accepting the
dependency, isolating/reimplementing the missing behavior, and owning a larger subsystem.
Choose the near-optimal balance.

If unstable calls remain, concentrate them in the smallest compatibility boundary and test
that boundary through the real framework lifecycle. Do not spread private framework state
through algorithm modules or solve the concern with needlessly restrictive point-version
pinning.

## 6. Keep one authority per decision

Selection, mutation RNG, stable member identity, checkpoint construction, Tune storage,
process-group lifecycle, and genome application each need a clear owner. Convenience must not
create a second source of truth.

## 7. Match support claims to evidence

Every version, device, topology, persistence, recovery, and performance claim must have
corresponding evidence. Dependency metadata indicates what users may attempt/install; it does
not automatically establish compatibility or production support.

## Result

- **Pass:** the claimed behavior has one coherent ownership model and the selected design is
  the best-supported balance among realistic alternatives.
- **Fail:** the unit changes Clan semantics, duplicates authority without benefit, hides user
  ownership, or leaves avoidable unstable coupling spread through the system.
- **Insufficient evidence:** the architecture may be sound, but the support claim has not yet
  been qualified.

## References

- [Product roadmap](../product_roadmap.md)
- [Public API](../api.md)
- [System behavior](../contracts/system_behavior.md)
- [Population invariants](../contracts/population_resolution_invariants.md)
- [Population responsibilities](../contracts/population_resolution_responsibilities.md)
- [Ray scheduler compatibility](../implementation/ray_scheduler_compatibility.md)
- [Current plan](../plan.md)
