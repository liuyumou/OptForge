# Agent Instructions

Implement one dependency-ready bounded task at a time. Follow
[CONTRIBUTING.md](CONTRIBUTING.md), accepted specifications, and ADRs.
Update state/active-task.md before work and record acceptance evidence afterward.
Read state/known-failures.md before implementing related behavior.

The current implementation scope is C1 (SPEC-0002 and ADR-0003), building on the
completed M1 contracts. Later solver executive, extension, scheduling, and GPU APIs
require their own specifications and acceptance gates; do not introduce them here.
Use Rust for runtime work; Python under tools/ is build and validation tooling,
not the SDK. Native HiGHS code is permitted only inside optimizer-highs behind its
private ownership boundary, with the pinned 1.11.0 CPU contract.

Run bash tools/check.sh for acceptance. Discovering GPUs does not authorize a
kernel workload; all actual project GPU jobs require the shared host lock.
Do not change experiment seeds, thresholds, splits, or defaults silently.
Do not publish, push, or configure external hosting without authorization.
