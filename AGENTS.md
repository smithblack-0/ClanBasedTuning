# Repository instructions for coding agents

Before substantial engineering, design, review, or documentation work:

1. Read [`docs/README.md`](docs/README.md) and [`STATUS.md`](STATUS.md).
2. Identify the requested result and the smallest coherent review unit.
3. Read the governing roadmap, decisions, architecture, active contracts, current source, tests, consumers, and framework evidence relevant to that unit.
4. Use [`docs/process/engineering.md`](docs/process/engineering.md) for engineering and review work.
5. Use [`docs/process/writing.md`](docs/process/writing.md) for substantial documentation.

Code and tests establish current behavior. Design documents establish accepted targets. Historical material under `docs/archive/` is evidence, not active authority.

Do not reconstruct intent from names or reuse a previous iteration merely because code already exists. Begin from the current accepted contract and inspect the whole affected boundary.

A pull request must:

- perform one coherent small-to-medium task;
- leave a stable, mergeable repository state;
- keep title, body, diff, tests, and documentation in sync;
- distinguish implemented behavior, accepted design, evidence, and future work; and
- avoid bundling unrelated design, implementation, integration, and cleanup.

Tentative reasoning may live in `scratchwork/` while useful. It does not override active authority and must not become a substitute for updating the artifact that owns an accepted correction.

Do not modify CI/workflow files, change product or milestone authority, broaden support claims, or merge pull requests without explicit authorization.
