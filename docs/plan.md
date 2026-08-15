# Remaining readiness gates

This plan begins from merged PR #52. The corrected function API and CPU mechanics are the
baseline; green mechanics are necessary evidence, not production completion.

## 1. Executable CPU and failure qualification

- Retain the exact scalar state-transfer contract.
- Add a small realistic MLP/AdamW contract with real forward/backward and optimizer restore.
- Prove insufficient resident capacity terminates through a bounded, diagnosable rendezvous
  failure rather than time-multiplexing a partial Clan into DDP.
- Keep destructive active-peer failure separately opt-in so ordinary CI does not deliberately
  kill live framework processes.

Exit: exact branch head passes pure, package, CPU framework, restore, and insufficient-capacity
contracts.

## 2. Hardware/topology qualification surfaces

- Keep the CUDA/NCCL test small: two Tune members, one GPU each, synthetic data, two-layer MLP,
  repeated Clan transition, no model download.
- Provide physical multi-node qualification against an existing Ray cluster, requiring shared
  Tune storage and proof that the two members actually ran on distinct nodes.
- Record hardware/software/topology with any passing evidence before broadening support claims.

Exit: tests are runnable from a checkout and self-skip when their required environment is not
present. Support remains a non-claim until the corresponding test is actually executed.

## 3. Diagnostics

- Emit standard Python logging for cohort registration/join, generation boundary progress,
  selected parent/child mutation values, checkpoint source, timeout/failure, and successful
  runtime release.
- Keep diagnostics at Clan ownership seams; do not replace Ray/Lightning/PyTorch logging.
- Avoid dumping arbitrary full user configs when only mutation-controlled keys are relevant.

Exit: an operator can identify cohort/member/round/selection/checkpoint/timeout/release state
without a second package-owned execution system.

## 4. Typing and distribution

- Ship `py.typed` only with an executable maintained package-source type-check contract.
- Build wheel and sdist, validate metadata, validate release rendering, install the wheel
  non-editably, and import the actual public surface from the installed artifact.
- Preserve broad major-version dependency bounds; qualification evidence, not point pinning,
  determines support.

Exit: static and built-artifact checks pass on the exact branch head.

## 5. Performance evidence

- Provide a no-download benchmark using the same tiny realistic workload.
- Record wall clock, Ray member time, checkpoint size/count, generation count, and final
  fitness on representative hardware.
- Do not invent a universal threshold from CI. Use measurements to decide whether restart
  overhead or actor reuse is materially important before reopening API design.

Exit: measurement tooling is reproducible. Performance claims require recorded representative
runs, not merely the existence of the script.

## 6. Security, release, and legal readiness

- Publish a vulnerability-reporting path that does not solicit exploit details in public.
- Maintain a pre-1.0 version/release checklist, changelog, build and `twine check` validation,
  and evidence-bounded release notes.
- Do not select a project license on behalf of the owner.

Exit: process/docs/artifact checks are ready; ordinary public release remains blocked until the
owner selects a license.

## 7. Documentation and examples synchronization

- Re-run the public API/example review after all new qualification surfaces exist.
- Keep userspace optimizer application visible.
- Make local GPU/multi-node/failure commands operational and distinguish runnable harnesses
  from directly qualified support.
- Ensure STATUS, API docs, README, examples, qualification records, and release policy tell the
  same story.

Exit: an implementer can install, run the CPU example, run applicable local qualification, and
understand every current non-claim without reading development history.

## 8. Final style and quality re-audit — mandatory last gate

This gate is performed only after gates 1–7 have been synchronized. Passing tests is input to
this review, not its conclusion.

Re-audit the shipped source, tests, examples, active docs, packaging, and release surfaces
against the authoritative project style/quality contract. At minimum review:

- fast, effective, maintainable, correct, and concise simultaneously;
- module/class/function documentation and complete type annotations;
- whether each retained function/method earns its abstraction, using useful documentation as
  a forcing function rather than a coverage target;
- dependency injection/construction boundaries and absence of hidden construction ownership;
- imports, module organization, and responsibility level;
- test isolation, documentation quality, no patching where injection should exist, and a few
  small realistic end-to-end contracts;
- Ray/Lightning/PyTorch ownership versus CBT ownership;
- userspace genome ownership and scientific validity boundaries;
- distribution/release truthfulness and dependency compatibility policy; and
- synchronization of README, API docs, examples, STATUS, qualification, and release records.

Any concrete issue found is corrected and the relevant executable evidence is rerun. A
function whose useful docstring can only paraphrase its name, signature, or obvious body is a
prompt to reconsider the abstraction; framework-required small methods are retained when their
interface role itself is the reason. External evidence gates such as owner license selection or
hardware that has not been run remain explicitly blocked/non-claimed rather than being waved
through by the code-quality audit.

### Gate result

Completed against executable commit `5f117df15b89d468663abdb6ec9e316ca89ca2b8`
after the initial audit was reopened for a documentation-driven abstraction pass. Exact
executable evidence is GitHub Actions run `31902897008`, which passed Python 3.11, Python 3.13,
and the real Ray/Lightning job. The audit result and remaining external blockers are recorded
in [`reviews/readiness_quality_audit.md`](reviews/readiness_quality_audit.md).
