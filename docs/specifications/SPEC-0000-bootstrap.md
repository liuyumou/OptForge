# SPEC-0000: Repository Bootstrap

Status: accepted
Scope: repository
Owner: engineering
Introduced: M0
Last reviewed commit: bootstrap (initial commit containing this file)
Supersedes: none
Implementation: [workspace](../../Cargo.toml), [CLI](../../crates/optimizer-cli/src/main.rs)
Tests: [CLI tests](../../crates/optimizer-cli/tests/cli.rs), [gate](../../tools/check.sh)

## Purpose

Establish an inspectable Rust project and acceptance process. Mathematical solving,
native FFI, CUDA kernels, Python SDK, and performance claims are outside M0.

## Terminology

A gate is the checks required before task completion. Bootstrap means M0 only.

## Requirements

1. The workspace MUST build and test on Linux with the pinned Rust toolchain.
2. CPU CI MUST run format, lint, tests, dependency/license, and artifact checks.
3. Public Rust API documentation MUST build without warnings.
4. Maintained documentation MUST build without broken internal links or anchors.
5. The hello command MUST print exactly hello workspace followed by a newline.
6. Unsupported commands and invalid lease arguments MUST exit with code 2.
7. The project MUST NOT imply that the bootstrap implements optimization solving.
8. GPU CI MUST use the single project concurrency group and host lease.
9. Every behavior change MUST update its specification, tests, changelog, and task evidence.

## Interfaces

optimizer hello; optimizer --help; optimizer --version.
GPU commands are defined in [SPEC-0006](SPEC-0006-gpu-lease.md).
Artifacts are defined in [SPEC-0007](SPEC-0007-artifacts.md).

## State and invariants

M0 produces no objective or optimality result. Numerical tolerances and solver
determinism are inapplicable. Stable hello output and sorted discovery are deterministic.

## Errors and recovery

Malformed commands produce diagnostics on stderr. Build/test failures block the
acceptance gate and require diagnosis recorded in state/known-failures.md.

## Compatibility and versioning

Workspace version 0.1.0. Public solver APIs are deferred; artifact formats are versioned.

## Security and resource limits

CPU checks use ordinary runner limits and workflow deadlines. GPU discovery and
simulations are bounded by SPEC-0006. Untrusted pull requests MUST NOT execute on
the self-hosted GPU runner.

## Examples

cargo run -p optimizer-cli -- hello prints hello workspace.

## Acceptance tests

Requirements 1-3: tools/check.sh and ci.yml.
Requirement 4: tools/build_docs.py and docs.yml.
Requirements 5-7: hello_and_invalid_arguments_follow_cli_contract.
Requirement 8: benchmark-smoke.yml and shell_runner_and_rust_use_the_same_host_lock.
Requirement 9: contributor workflow and task evidence.

## Open questions

Remote branch protection and runner provisioning await hosting configuration.
