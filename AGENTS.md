# Agent Instructions

Implement one dependency-ready bounded task at a time. Follow
[CONTRIBUTING.md](CONTRIBUTING.md), accepted specifications, and ADRs.
Update state/active-task.md before work and record acceptance evidence afterward.
Read state/known-failures.md before implementing related behavior.

The current implementation scope is M1 (SPEC-0001 and ADR-0002). Later solver APIs
require their own specifications and acceptance gates. Do not introduce speculative solver types.
Use Rust for runtime work; Python under tools/ is build and validation tooling,
not the SDK. Keep unsafe and native dependencies deferred until their contract.

Run bash tools/check.sh for acceptance. Discovering GPUs does not authorize a
kernel workload; all actual project GPU jobs require the shared host lock.
Do not change experiment seeds, thresholds, splits, or defaults silently.
Do not publish, push, or configure external hosting without authorization.
