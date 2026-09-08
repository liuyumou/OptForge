# Active Task

Objective: synchronize the project to https://github.com/liuyumou/OptForge.git.

Status: complete.

Acceptance gate: origin points to the requested repository; main is pushed with
upstream tracking; the remote main revision matches local HEAD; the worktree is
clean. Preserve existing history and validate updated documentation.

Expected changes: Git remote/tracking configuration and repository hosting/task
records. Resource budget: bounded CPU checks and Git operations; no GPU work.

Evidence: the original main history was pushed successfully and main now tracks
origin/main. The complete tools/check.sh gate passed, including 8 Rust tests,
8 artifact tests, dependency policy, documentation, and smoke validation. Hosting
records identify the remote. The synchronization includes this documentation
update; remote revision equality and clean worktree are checked after its push.

## M0 Bootstrap Evidence

Objective: implement M0 from implementation-plan.md.

Status: complete.

Acceptance gate: pinned Rust workspace builds; format, Clippy, tests, dependency
policy, rustdoc, documentation links/build, schemas, and benchmark smoke pass.
GPU discovery must report available UUIDs or an explicit unavailable state.
Simulated jobs must serialize and release ownership after cancellation or exit.

Expected changes: repository bootstrap, crates, tools, schemas, CI, documentation,
examples, benchmark fixtures, and task state. Preserve both original plans.

Resource budget: CPU-only builds and bounded tests; GPU discovery only, no kernels.
One developer, one bounded milestone. M1-M6 remain dependency-ordered backlog.

Evidence before initial commit: Rust workspace build, format, warnings-as-errors
Clippy, 8 Rust unit/integration tests, rustdoc, cargo-deny (advisories, bans,
licenses, sources), 8 Python artifact tests, schema/provenance validation, shell
syntax, and a 33-page documentation/link build passed. Discovery returned all
three expected physical GPU UUIDs without launching kernels.

Clean-checkout acceptance: the complete tools/check.sh gate passed on revision
a628c0c8605dd2434cdf7fd775fae85e96423a31 in an independent local clone at
/tmp/ai-optimizer-m0-verification. It rebuilt every crate and generated a validated
measured smoke record with dirty=false. No acceptance checks were waived.

Verified lease cases: competing-process timeout and serialization, normal release,
SIGINT while waiting, SIGTERM while holding, SIGKILL recovery, and interoperability
with the shell runner's flock primitive. All were CPU simulations. Inventory
reported two RTX 5090 devices and one RTX PRO 6000 by their expected UUIDs.

Artifacts: the clean-clone record is at
/tmp/ai-optimizer-m0-verification/artifacts/bootstrap-smoke.json. The workspace
runner can reproduce artifacts/bootstrap-smoke.json. Records measure CLI startup
only; no solver or GPU performance result is claimed.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 were installed under
/tmp/ai-optimizer-cargo with RUSTUP_HOME=/tmp/ai-optimizer-rustup. Documentation
and schema tooling use /tmp/ai-optimizer-venv. Hosting workflows are configured
but were not run on GitHub; remote protection and GPU-runner provisioning remain
external setup, as documented in state/known-failures.md.

Follow-up: M1 is dependency-ready. Write SPEC-0001-model-and-validation.md, then
implement the original-model numerical authority boundary and its independent
property/exhaustive tests. No M1 behavior has been implemented as part of M0.
