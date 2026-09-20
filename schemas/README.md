# Artifact Schemas

Every schema uses JSON Schema draft 2020-12. These are normative interfaces under
[SPEC-0007](../docs/specifications/SPEC-0007-artifacts.md).

- [Run configuration](run-config-v1.schema.json)
- [Benchmark manifest](benchmark-manifest-v1.schema.json)
- [Experiment result](experiment-result-v1.schema.json)
- [Solve configuration](solve-config-v1.schema.json) at version 1 and
  [solve record](solve-record-v2.schema.json) at version 2, normative under
  [SPEC-0002](../docs/specifications/SPEC-0002-backend-contract.md). The two carry
  separate versions: the record gained a settings block under
  [SPEC-0011](../docs/specifications/SPEC-0011-gpu-lp-backend.md) while the
  configuration did not change, and a configuration is embedded in the search
  configuration where a record is embedded nowhere.
- [First-order LP settings](lp-settings-v1.schema.json), normative under
  [SPEC-0011](../docs/specifications/SPEC-0011-gpu-lp-backend.md) requirements 9
  and 10. A solve record embeds this document when the backend that wrote it has
  such settings.
- [Search configuration](search-config-v3.schema.json) and
  [search record](search-record-v3.schema.json) at version 3, normative under
  [SPEC-0003](../docs/specifications/SPEC-0003-solver-executive.md),
  [SPEC-0004](../docs/specifications/SPEC-0004-extension-runtime.md) and
  [SPEC-0010](../docs/specifications/SPEC-0010-heterogeneous-computation.md)
- [Run record](run-record-v2.schema.json) at version 2, normative under
  [SPEC-0005](../docs/specifications/SPEC-0005-run-surface.md)
- [Extension registry](extension-registry-v1.schema.json) and
  [conformance record](conformance-record-v1.schema.json), normative under
  [SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md)

- [LP manifest v2](lp-manifest-v2.schema.json), the ADR-0022 development
  extension: a `mixed` family, generator version 2, a larger byte cap, an
  explicit `extends` reference to the frozen v1 development manifest and a
  per-instance solve limit. Version 1 manifests are unchanged.
- Forthcoming under [SPEC-0014](../docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md)
  and ADR-0023: lp-batch-request-v1 and lp-batch-endpoint-v1 for GPUP-THROUGHPUT
  repeated-solve sessions. They land with the implementation phase as new
  versioned files; per the versioning rule below, each version lives in its
  filename and is pinned inside the document by a `const`.

Use python3 tools/validate_artifacts.py from the repository root. Schema validation
is supplemented with file checksum, configuration, hardware, and timing checks.
optimizer-experiment embeds these same files; there is no separately maintained
Rust representation to drift from the bootstrap contract.

Search and run records are validated by the same tooling and by the Rust parsers
in optimizer-solver and optimizer-experiment. Both authorities must accept the
same documents, so nested `schema_version` values are checked on the Rust parse
path too rather than only by the schemas.

Registry and conformance documents follow the same rule through
optimizer-registry's parsers. Two registry rules are cross-field and cannot be
expressed in JSON Schema — that an entry's authority follows from its category, and
that no two entries share an identity — so the validator checks them in Python
beside the schema, and the integration tests pair each against the Rust parser
rather than against the schema alone. A promoted entry's conformance record is read
and re-hashed during validation, so a promotion claim in a committed registry
cannot be stale.

M1 model, candidate and validation-report JSON are separate from experiment
artifacts. Their normative version-1 shape is defined in
[SPEC-0001](../docs/specifications/SPEC-0001-model-and-validation.md) and enforced
by optimizer-core's typed parser and contract tests. Candidate infeasibility is
not an experiment-result solver status.

A version lives in the filename and is pinned inside the document by a `const`, so
a document and its schema cannot disagree about which one it is. A breaking change
is a new versioned file, never an edit to an existing one, and a mismatch is refused
rather than migrated.

Three of these moved together for one field. SPEC-0010 put the selected device on
the search configuration; a search record embeds its configuration and a run record
embeds that search record, so `search-config`, `search-record` and `run-record` all
moved at once. That cascade is the cost of keeping the device somewhere verification
reads, and it was paid deliberately rather than avoided by putting the device in
provenance, where a re-execution would never see it.

## LP study artifacts

SPEC-0013 defines separate [campaign](lp-campaign-v1.schema.json),
[manifest](lp-manifest-v1.schema.json), [endpoint](lp-endpoint-v1.schema.json),
[trial](lp-trial-v1.schema.json) and append-only [ledger event](lp-ledger-v1.schema.json)
version-1 documents. The endpoint embeds an unchanged solve-record-v2. Strict
schema validation is supplemented by independent Rust endpoint checking, grouped
partition/configuration checks and durable reservation/settlement validation.
These are not a migration of SPEC-0007 smoke artifacts or the general C10 runner.
See [study operations](../docs/benchmarks/lp-precision-study.md).
