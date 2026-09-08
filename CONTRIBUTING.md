# Contributing

Purpose: keep every change buildable, specified, and reproducible. Scope: all
repository work, including autonomous development.

## Task workflow

1. Read [status](wiki/status.md), [backlog](state/backlog.yaml), relevant
   specifications and ADRs, [known failures](state/known-failures.md), and tests.
2. Update [active task](state/active-task.md) with objective, acceptance gate,
   likely files, and a bounded CPU/GPU resource budget.
3. Specify new behavior before implementation using the
   [specification template](docs/specifications/TEMPLATE.md). A public or default
   feature requires an accepted specification.
4. Implement one complete vertical slice and meaningful contract tests.
5. Run `bash tools/check.sh` plus relevant hardware or benchmark checks.
6. Diagnose failures; preserve minimized fixtures and record unresolved issues.
7. Update specifications, changelog, evidence, and task state in the same change.
8. Commit after the acceptance gate passes, then select the next dependency-ready
   task. The bootstrap's first commit may precede the measured smoke because
   its source revision does not exist until that commit is created.

One AI developer works on one bounded task at a time. Numerical ambiguity blocks
the affected implementation; independent documentation and tooling may continue.
Never silently change splits, seeds, tolerances, thresholds, or solver defaults.
Such changes require a new ADR and experiment record.

## Git rules

Use protected, buildable `main` and short branches named `type/description`.
Rebase before integration. Use Conventional Commits: feat, fix, refactor, perf,
test, docs, build, ci, bench, chore. Keep commits focused and inspect lockfile
changes. Revert shared changes with new commits. Never rewrite shared history.
Behavior changes require specifications, tests, release notes, and successful CI.

Do not commit credentials, private datasets, binaries, unproven benchmark output,
or dependency updates that have not passed policy checks. See
[release operations](docs/operations/release.md) for hosting configuration and tags.

## Tests and documentation

See [test strategy](docs/architecture/testing.md) and
[documentation rules](docs/operations/documentation.md). Performance measurements
do not establish mathematical correctness. A timeout or numerical failure must
never imply proven optimality.

## Resource ownership

Every project GPU job must use the shared host lease described in
[GPU operations](docs/operations/gpu.md). Do not run multiple device jobs
simultaneously. CPU simulation tests use isolated temporary locks and no devices.
