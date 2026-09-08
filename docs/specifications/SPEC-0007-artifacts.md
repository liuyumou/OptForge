# SPEC-0007: Bootstrap Artifact Formats

Status: accepted
Scope: experiment artifacts
Owner: optimizer-experiment
Introduced: M0
Last reviewed commit: bootstrap (initial commit containing this file)
Supersedes: none
Implementation: [schemas](../../schemas/README.md), [validator](../../tools/validate_artifacts.py), [smoke runner](../../tools/benchmark_smoke.py)
Tests: [artifact contracts](../../tests/integration/test_artifacts.py)

## Purpose

Define versioned configuration, benchmark manifest, and result records before
solver execution. These schemas are artifact shapes, not mathematical status proofs.

## Terminology

A manifest identifies instances, hashes, split, license, seeds, configuration, and
timing. An example illustrates a shape. A measured result records an actual run.

## Requirements

1. Records MUST validate against their versioned JSON Schema draft 2020-12 file.
2. Schemas MUST reject unknown fields except explicitly declared generator parameters.
3. Configurations MUST include seed, positive time/memory/thread limits, device, and settings.
4. M0 configurations MUST reject unimplemented solver settings.
5. Manifests MUST include unique instance IDs, relative repository paths, SHA-256 hashes, source, license, split, and seeds.
6. Validation MUST verify local instance hashes and reject repository path escapes.
7. Results MUST include manifest hash, Git revision, dirty state, hardware, toolchain, configuration, timing, status, warnings, and error.
8. Result configuration and timing protocol MUST match the referenced manifest.
9. CPU records MUST NOT claim GPU execution; GPU records MUST identify the selected UUID, name, and driver.
10. A measured result MUST NOT use the example all-zero revision.
11. M0 MUST NOT accept an optimal status or claim mathematical proof.
12. Failure, infeasible, unbounded, unsupported, and smoke records MUST have a null objective.
13. Backend-failure records MUST retain an error diagnostic.
14. JSON input MUST reject duplicate keys and non-finite numerical constants.
15. Benchmark split, seed, tolerance, acceptance-threshold, or default changes MUST have an ADR and a new record.

## Interfaces

[Run config](../../schemas/run-config-v1.schema.json),
[manifest](../../schemas/benchmark-manifest-v1.schema.json), and
[result](../../schemas/experiment-result-v1.schema.json) define required fields.
python3 tools/validate_artifacts.py validates committed examples and manifests.
Add --result PATH to validate a generated result and its manifest provenance.

## State and invariants

Schema version is 1. SHA-256 is 64 lowercase hex characters; Git revision is
40 lowercase hex characters. Seeds are unsigned 32-bit integers. Memory is MiB,
limits are milliseconds, elapsed timing is integer nanoseconds on a monotonic
clock. Python integer parsing is unbounded; Rust inventory arithmetic is checked.
M0 emits no objective and defines no solver numerical tolerance.
Serialization is UTF-8 JSON; schema order is not semantically significant.
Reproducibility requires recording dirty state; publishable evidence should use a
clean revision. M0 validation checks revision shape, not remote Git object existence.

## Errors and recovery

Malformed JSON, unknown schema versions, hash/configuration/device mismatches,
missing files, and invalid fields fail validation with a diagnostic and nonzero
exit. No automatic repair or silent defaults are permitted.

## Compatibility and versioning

Breaking format changes require a new versioned schema file and migration notes.
Later accepted solver specifications must define statuses, objective validity,
tolerances, and optimality evidence before extending these records.

## Security and resource limits

Tools validate trusted local project records and fixtures; they are not a public
upload service. Do not load untrusted arbitrarily large inputs. Resolve fixture
and manifest paths inside the repository and resolve schema references from the
local registry. The smoke runs one hello process with a 10-second timeout and
512 MiB address-space limit; it records startup overhead and excludes build time.

## Examples

[Configuration](../../examples/run-config.json),
[manifest](../../benchmarks/manifests/bootstrap-smoke.json),
[example result](../../examples/experiment-result.json).
The example is explicitly synthetic and has no performance interpretation.

## Acceptance tests

ArtifactContracts covers required metadata, unsupported fields/settings/versions,
non-finite and duplicate JSON, failure objective/status behavior, fixture tampering,
path escape, config/manifest/device mismatch, and all declared status shapes.
The smoke runner produces a measured record and validates it before success.

## Open questions

Solver proof fields, aggregate performance reports, dataset retrieval and Python
SDK bindings remain future contracts. No test split is frozen beyond bootstrap.
