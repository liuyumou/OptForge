# Artifact Schemas

Version 1 uses JSON Schema draft 2020-12. These are normative interfaces under
[SPEC-0007](../docs/specifications/SPEC-0007-artifacts.md).

- [Run configuration](run-config-v1.schema.json)
- [Benchmark manifest](benchmark-manifest-v1.schema.json)
- [Experiment result](experiment-result-v1.schema.json)

Use python3 tools/validate_artifacts.py from the repository root. Schema validation
is supplemented with file checksum, configuration, hardware, and timing checks.
optimizer-experiment embeds these same files; there is no separately maintained
Rust representation to drift from the bootstrap contract.

M1 model, candidate and validation-report JSON are separate from experiment
artifacts. Their normative version-1 shape is defined in
[SPEC-0001](../docs/specifications/SPEC-0001-model-and-validation.md) and enforced
by optimizer-core's typed parser and contract tests. Candidate infeasibility is
not an experiment-result solver status.
