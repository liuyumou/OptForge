# Artifact Schemas

Version 1 uses JSON Schema draft 2020-12. These are normative interfaces under
[SPEC-0007](../docs/specifications/SPEC-0007-artifacts.md).

- [Run configuration](run-config-v1.schema.json)
- [Benchmark manifest](benchmark-manifest-v1.schema.json)
- [Experiment result](experiment-result-v1.schema.json)
- [Solve configuration](solve-config-v1.schema.json) and
  [solve record](solve-record-v1.schema.json), normative under
  [SPEC-0002](../docs/specifications/SPEC-0002-backend-contract.md)
- [Search configuration](search-config-v2.schema.json) and
  [search record](search-record-v2.schema.json) at version 2, normative under
  [SPEC-0003](../docs/specifications/SPEC-0003-solver-executive.md) and
  [SPEC-0004](../docs/specifications/SPEC-0004-extension-runtime.md)
- [Run record](run-record-v1.schema.json), normative under
  [SPEC-0005](../docs/specifications/SPEC-0005-run-surface.md)

Use python3 tools/validate_artifacts.py from the repository root. Schema validation
is supplemented with file checksum, configuration, hardware, and timing checks.
optimizer-experiment embeds these same files; there is no separately maintained
Rust representation to drift from the bootstrap contract.

Search and run records are validated by the same tooling and by the Rust parsers
in optimizer-solver and optimizer-experiment. Both authorities must accept the
same documents, so nested `schema_version` values are checked on the Rust parse
path too rather than only by the schemas.

M1 model, candidate and validation-report JSON are separate from experiment
artifacts. Their normative version-1 shape is defined in
[SPEC-0001](../docs/specifications/SPEC-0001-model-and-validation.md) and enforced
by optimizer-core's typed parser and contract tests. Candidate infeasibility is
not an experiment-result solver status.
