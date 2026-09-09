# ADR-0003: Pinned CPU HiGHS Boundary

Status: accepted
Owner: numerical backend
Introduced: C1
Last reviewed commit: 9b42b62
Supersedes: ADR-0002's M1-only scope and ADR-0001's native-library deferral

## Context

The capability roadmap requires a real LP/MILP backend before
scheduling incumbents and owned search. M1 validation remains authoritative for
original candidate feasibility, while native termination has numerical assumptions.

## Decision

Implement [SPEC-0002](../specifications/SPEC-0002-backend-contract.md) against
HiGHS 1.11.0, MIT licensed, from the upstream source archive at
https://codeload.github.com/ERGO-Code/HiGHS/tar.gz/refs/tags/v1.11.0.
The archive SHA-256 is
2b44b074cf41439325ce4d0bbdac2d51379f56faf17ba15320a410d3c1f07275.
Use static CPU builds, 32-bit HighsInt, no CUDA, no zlib and one solver thread.
Build the standalone executable from the same source for differential testing.
Permit unsafe only inside optimizer-highs's private native boundary; retain
workspace prohibition for every other runtime crate. A workspace-level `forbid`
cannot be relaxed by an inner crate, so optimizer-highs declares its own
`[lints.rust]` block instead of inheriting the workspace lints, keeping
`unsafe_op_in_unsafe_fn` denied there. Explicitly serialize use of the native
global scheduler. Rust owns all runtime orchestration.

Provisioning stays out of tracked source: tools/setup_highs.sh builds the pinned
library under target/native, and the crate's build script links it only when both
the archive and the C API header are present. A build without the library exposes
the same API and reports an explicit unsupported backend.

Native settings must be explicit and recorded. Existing M0/M1 seeds, tolerances,
defaults, schema versions and smoke protocol do not change. New experiments
receive distinct manifests and their settings are frozen before measurements.

## Alternatives

A command-line-only adapter would not establish the required FFI lifecycle and
warm-start contract. Floating system packages obscure ABI and provenance.
Reimplementing an LP solver would exceed C1 and remove the independent reference.

## Consequences

CPU builds require CMake and a C++ compiler. Native source and binaries remain
outside tracked source. Sanitizers supplement Rust tests because ownership
inside foreign code is outside Rust's guarantees. Backend optimality is reported
under numerical assumptions, not as an exact certificate. Skipping the native
build in the acceptance gate leaves SPEC-0002's differential, status-mapping and
cancellation evidence uncovered, so the gate reports that case explicitly rather
than passing silently. C2-C7 require their own accepted contracts before
implementation.

## Implementation and Tests

Implementation and acceptance evidence are recorded in
[active task](../../state/active-task.md). C1 is not complete until its full gate
and native acceptance tests pass.
