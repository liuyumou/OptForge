# Agent Instructions

Implement one dependency-ready bounded task at a time. Follow
[CONTRIBUTING.md](CONTRIBUTING.md), accepted specifications, and ADRs.
Update state/active-task.md before work and record acceptance evidence afterward.
Read state/known-failures.md before implementing related behavior.

M1, C1, C2, C3, C4 and C5 are complete and specified. The next dependency-ready
task is C8, the local extension registry, whose contract is accepted as SPEC-0009
and ADR-0008; implement it against that contract and do not widen it. The registry
resolves a named extension identity to an extension this build provides; it
deliberately does not load dynamically distributed native components, which would
need a second unsafe boundary ADR-0003 prohibits. The Python SDK (C9) and the
comparative experiment runner (C10) are unspecified, and
[known failures](state/known-failures.md) records each blocker. Later SDK,
comparative-runner and GPU APIs require their own specifications and acceptance
gates; do not introduce them without one.
Use Rust for runtime work; Python under tools/ is build and validation tooling,
not the SDK. Native HiGHS code is permitted only inside optimizer-highs behind its
private ownership boundary, with the pinned 1.11.0 CPU contract. That crate
declares its own lints because a workspace-level unsafe prohibition cannot be
relaxed per crate; every other runtime crate keeps the prohibition.

Run bash tools/check.sh for acceptance; it requires the pinned native HiGHS build.
AI_OPTIMIZER_SKIP_NATIVE=1 skips it and reports uncovered native acceptance, which
must never be recorded as a full gate pass. Discovering GPUs does not authorize a
kernel workload; all actual project GPU jobs require the shared host lock.
Do not change experiment seeds, thresholds, splits, or defaults silently.
Do not publish, push, or configure external hosting without authorization.
