# ADR-0001: Bootstrap Boundaries and Tooling

Status: accepted
Owner: architecture
Introduced: M0
Last reviewed commit: bootstrap (initial commit containing this file)
Superseded by: none

## Context

The implementation plan starts with a buildable repository and engineering process.
Later milestones require mathematical contracts that are not yet specified.

## Decision

Create the seven Rust ownership crates, with no speculative numerical APIs. Use
Rust 1.93.1 (including stable file locking), MIT licensing, serde JSON, a CSV parser,
and ctrlc for cooperative Linux signal handling. Do not link HiGHS or CUDA yet.
Use Python-Markdown as the allowed equivalent documentation builder and jsonschema
draft 2020-12 for build-time artifact validation. This tooling is not a Python SDK.
Use cargo-deny for dependency sources, licenses, bans, and vulnerability advisories.
Rust dependencies are pinned by Cargo.lock; CI installs cargo-deny 0.19.0.
Do not add nextest until CI capacity makes an additional tool worthwhile.

## Alternatives

A full solver skeleton would create unsupported abstractions before specifications.
mdBook is viable but adds another compiled tool while Python already provides
standards-compliant JSON Schema validation. Hand-written schema validation would
risk diverging from draft 2020-12. PID-file leases require unsafe stale-owner logic.

## Consequences

M0 is inspectable and CPU-buildable without native solver libraries. Python 3.11+
is required for tooling only. GPU ownership uses a cooperative OS file lock;
deployment must ensure all jobs share its inode. These choices do not establish
solver correctness or performance.

## Implementation and tests

[Workspace](../../Cargo.toml), [dependency policy](../../deny.toml),
[complete gate](../../tools/check.sh), [documentation builder](../../tools/build_docs.py),
[lease contract](../specifications/SPEC-0006-gpu-lease.md).
