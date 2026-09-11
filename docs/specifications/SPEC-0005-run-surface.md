# SPEC-0005: Agent-Independent Run Surface

Status: accepted
Scope: optimizer-experiment run records and the optimizer-cli search/verify surface
Owner: research infrastructure
Introduced: C4
Last reviewed commit: 692e19f
Supersedes: none
Implementation: [run records](../../crates/optimizer-experiment/src/run.rs), [checksums](../../crates/optimizer-experiment/src/sha256.rs), [search command](../../crates/optimizer-cli/src/search.rs), [provenance](../../crates/optimizer-cli/src/provenance.rs), [validator](../../tools/validate_artifacts.py)
Tests: [run surface contracts](../../crates/optimizer-cli/tests/search.rs), [record contracts](../../crates/optimizer-experiment/tests/run.rs), [schema contracts](../../tests/integration/test_run_records.py)

## Purpose

Make a search performed by one agent independently repeatable by someone who
has only its record. The [C2 executive](SPEC-0003-solver-executive.md) and the
[C3 extension runtime](SPEC-0004-extension-runtime.md) are today reachable only
from Rust test code; this specification gives them a command surface, wraps each
search in a provenance-bearing run record, and defines verification as
re-execution rather than as trust in a stored result.

Reproducibility here is a falsifiable property, not a claim in prose. A run
record names the exact revision, model bytes, configuration and toolchain that
produced it, and `verify` re-runs the search from that record alone and fails on
disagreement. Agreement between two runs is evidence of determinism. It is not a
proof of optimality, and it does not upgrade any claim C2 or C3 declined to
make: a forfeited search stays forfeited however many times it is repeated.

Excluded: the local extension registry, including registration, promotion,
licenses, compatibility and inter-extension interactions; the Python SDK and any
foreign-function boundary; MCP adapters; restart from a checkpoint, which
[SPEC-0003](SPEC-0003-solver-executive.md) defines but does not implement;
incremental progress streaming during a search; comparative experiment
execution over a benchmark manifest, which remains
[SPEC-0007](SPEC-0007-artifacts.md)'s artifact contract without a runner;
scheduling producers (C5); GPU execution and device selection (C6); portfolio
allocation (C7). No performance claim is made or measured here.

## Terminology

A run is one execution of the search executive through the command surface. A
run record is the versioned document describing one run: the complete search
record plus the provenance needed to repeat it. Provenance is the set of facts
identifying what produced a record — source revision, dirty state, hardware,
toolchain, backend identity and version, and the hashed input documents.
Verification is re-executing a run from its record and comparing the two search
records. Agreement is the absence of any difference verification examines.
Divergence is any difference verification examines. A model fingerprint is
[SPEC-0001](SPEC-0001-model-and-validation.md)'s hash of the canonical model
document, which identifies model bytes rather than model identity.

## Requirements

1. A run record MUST contain its schema version, a record identifier, the source
   revision, the dirty state of that source, hardware, toolchain, the canonical
   model fingerprint, the hashed input documents, the complete search record,
   and warnings. A record missing any of these MUST be refused at parse time.
2. A run record MUST embed the search record verbatim, including its
   configuration, node counters, forfeiture state and per-extension summaries.
   It MUST NOT summarize, replace or omit any part of it, so a reader can see
   whether extensions influenced the run without consulting another document.
3. Parsing a run record MUST validate the versions of the documents nested
   inside it, not only its own, matching SPEC-0003 requirement 22.
4. The recorded model fingerprint MUST be computed from the canonical model
   document, not from its file bytes or its `model_id`.
5. A run record MUST record dirty source state as measured. A dirty record MUST
   NOT be presented as reproducible evidence, matching SPEC-0007 requirement 10
   for measured results.
6. `optimizer search` MUST accept a model document and a search configuration,
   run the executive over the pinned backend, and write a run record.
7. `optimizer search` MUST write a run record for every completed search,
   including one that reached a limit or was interrupted. Suppressing the record
   of an unfinished search is forbidden: the record states what happened.
8. `optimizer search` MUST NOT write a record when the run could not start,
   because the inputs were invalid, unreadable or unsupported. Such a failure is
   an error, not a run.
9. `optimizer verify` MUST re-run the search using only the configuration
   embedded in the record and the model document it is given. It MUST NOT read
   the recorded outcome, objective, bound or counters as inputs to that run.
10. `optimizer verify` MUST refuse a record whose embedded model fingerprint
    differs from the fingerprint of the model it is given, even when `model_id`
    is unchanged.
11. `optimizer verify` MUST report divergence in any of the search outcome, the
    recomputed objective, the dual bound, the gap, the forfeiture state, the
    explored-node count, both prune counters, the remaining-open-node count or
    the relaxations-solved count, and MUST name the diverging field.
12. `optimizer verify` MUST NOT treat a difference in measured elapsed time as
    divergence, because elapsed time is a measurement of the host rather than a
    property of the search.
13. Verification MUST NOT strengthen a claim. Agreement MUST NOT be reported as
    proven optimality, and a record whose search forfeited its proof claim MUST
    remain forfeited after agreement.
14. A search configuration naming an extension policy MUST be refused as
    unsupported by this surface, because no mechanism here loads an extension.
    Silently running the search without the named extension is forbidden: the
    resulting record would describe a search the caller did not request.
15. Both commands MUST use the established CLI exit mapping: 0 for a completed
    outcome, 1 for a limit or unresolved outcome, 2 for an argument, input,
    document, unsupported, numerical or backend error and for divergence, and
    130 for an interruption.
16. Both commands MUST categorize failures using the existing stderr prefixes
    and MUST NOT write a partial document to standard output on failure.
17. Cancellation MUST be cooperative and MUST produce a written record with an
    interrupted outcome and exit 130, not a discarded run.
18. Input documents MUST be bounded by the existing 16 MiB limit and MUST be
    read before the search starts, so a malformed input is an input error rather
    than a backend failure.
19. A run record MUST omit an unavailable or nonfinite measurement rather than
    serializing null in place of a number, matching SPEC-0002 requirement 11 and
    SPEC-0003 requirement 22.
20. The run record MUST have a JSON Schema, and that schema and the Rust parser
    MUST accept the same documents. Neither MUST be laxer than the other.

## Interfaces

```
optimizer search --model <path> --config <path> [--output <path>]
optimizer verify --record <path> --model <path>
```

`search` reads a version-1 model document and a version-2 `SearchOptions`
document, runs the executive, and writes a run record to `--output` or to
standard output when it is absent. `verify` reads a run record and a model
document, re-runs, and prints a verification result naming the compared fields.

`RunRecord` is a strict versioned object containing `schema_version`,
`record_id`, `revision`, `dirty`, `hardware`, `toolchain`, `model_fingerprint`,
`inputs`, `search` and `warnings`. Every field is required.

`InputDocument` carries `role`, `path` and `sha256` for one input, so a record
identifies the bytes it consumed rather than only their location. `role` is
`model` or `config`.

`Hardware` carries `os`, `cpu`, `logical_cpus`, `gpu_uuid`, `gpu_name` and
`driver`. `Toolchain` carries `rustc` and `cargo`. Both reuse the field names
SPEC-0007's experiment result already fixed, so the two provenance shapes cannot
drift apart. A CPU run leaves the three GPU fields null; this surface performs no
GPU work.

`search` is the embedded `SearchRecord` defined by SPEC-0003 at search schema
version 2, carrying the relaxation backend's own reported version rather than a
version this surface assumes.

`EnvironmentDifference` reports whether the backend library, source revision or
compiler performing a verification differs from the one a record names. It is
diagnostic: it is computed after the search runs, it is never consulted when
deciding agreement, and the backend difference is labeled distinctly because a
rebuilt library can change a search's counters while a moved revision alone
cannot. Making any of it decide an outcome would change what agreement means and
requires a new record version and an ADR.

`RunRecord::verify_agreement` compares two search records under requirements 11
and 12 and is the single authority for agreement. The command surface and the
contract tests use that one implementation, so a field cannot be compared by one
and ignored by the other.

`RUN_SCHEMA_VERSION` is 1. The run record schema is
[run-record-v1](../../schemas/run-record-v1.schema.json) and the embedded search
record schema is
[search-record-v2](../../schemas/search-record-v2.schema.json), whose version is
2 because SPEC-0004 moved search documents to version 2.

## State and Invariants

M1 model, tolerance and candidate semantics are unchanged. C1 solve semantics
and C2 search semantics are unchanged; this specification adds no requirement to
either contract and no mathematical authority of any kind. It observes and
records what the executive already decided.

A run record is immutable once written. Verification never edits a record; it
produces a verdict about one.

Determinism is inherited, not established here. The executive's node ordering is
a total order with a node-identity tiebreak, extension invocation is ordered by
extension identity, and every budget is a count rather than a duration, so two
runs of one configuration explore the same tree in the same order. This surface
depends on those properties and does not re-derive them. It follows that
divergence indicates a change in the engine, the backend library, the model
bytes or the host's floating-point behavior, and verification reports the field
rather than diagnosing the cause.

Elapsed time is recorded and excluded from agreement. The record therefore
contains a measurement no verification asserts, which is deliberate: the number
is useful for diagnosis and unusable as a contract.

A record is bound to model bytes through the fingerprint and to source through
the revision. Neither binding is cryptographic proof of provenance; both
identify rather than attest. A dirty record identifies a source state that no
revision can reconstruct, which is why requirement 5 forbids presenting it as
evidence.

## Errors and Recovery

Categories reuse `ErrorKind`: document, structural, candidate, tolerance,
numerical, unsupported, backend. Stderr prefixes reuse the established
`argument:`, `io:`, `document:` and `unsupported:` categories.

An unreadable or oversized input, a malformed document, an unsupported schema
version, an unsupported thread count, and a configuration naming an extension
policy are all errors before any search begins, and none writes a record. A
relaxation backend failure or numerical failure is a search outcome the executive
already defines; the record is written and the exit code is 2, because a failed
search is not a completed one.

Divergence is not a crash. Verification completes, names the diverging field,
and exits 2. A missing pinned native library is an unsupported error rather than
a divergence, because no search ran to compare.

Cancellation during a search sets the shared token, the executive observes it at
its node boundary, and the run is recorded as interrupted. Cancellation before
the search starts is an interruption with no record.

## Compatibility and Versioning

`RunRecord` is a new document at `schema_version` 1. The embedded search record
stays at SPEC-0003's version 2 and is not re-versioned by being embedded.

A breaking change to the run record requires a new versioned schema file, a new
Rust version constant and migration notes. Version mismatches are rejected
rather than migrated, matching SPEC-0004's treatment of version-1 search
documents.

Adding a field verification examines is a breaking change to the meaning of
agreement, because a record produced before that change was never compared on
it. Such a change requires a new record version and an ADR.

The command surface may add commands and optional flags compatibly. Changing an
exit code's meaning, a stderr category or a field's role in agreement is
breaking.

## Security and Resource Limits

Both commands read trusted local project documents and are not a service for
untrusted input. Input documents are bounded at 16 MiB, as the existing model and
solve commands already bound them. Output is written to a caller-named path; no
path is created outside it, and no record is written outside the caller's
request.

Search budgets are the caller's, taken from the configuration: node limit, time
limit and open-node limit are all explicit, and there are deliberately no
defaults. Verification costs a second full search, which is bounded by the same
budgets the record carries. A caller verifying an unbudgeted record therefore
accepts an unbounded second run, and the record's configuration is visible before
verification starts.

Provenance collection runs `git`, `rustc`, `cargo` and a CPU inventory command as
child processes with bounded output. It links no native library beyond the pinned
backend and creates no CUDA context. No network access is performed.

## Examples

```bash
optimizer search --model examples/model-v1.json \
  --config examples/search-config-v2.json --output artifacts/run.json
optimizer verify --record artifacts/run.json --model examples/model-v1.json
```

The example model minimizes `2 x3 + x8 + 0.5` subject to `x3 + x8 >= 2` with
`x3` binary and `x8` continuous and nonnegative. The search reports
`proven_optimal` with objective 2.5, matching the C1 solve of the same model, and
verification agrees and exits 0. Perturbing a coefficient in the model and
verifying again is refused on the fingerprint. Editing the recorded objective is
refused as divergence.

[The example record](../../examples/run-record-v1.json) is marked as an example
and uses the all-zero revision, so it cannot be read as measurement evidence.

## Acceptance Tests

Requirements 1-5: a produced record carries every provenance field, its
fingerprint matches the canonical model rather than the file bytes, a record with
a missing or unknown field is refused, and a wrong nested version is rejected by
both the Rust parser and the artifact validator. Requirements 6-8: a completed
search writes a record and exits 0; an invalid input writes none and exits 2 with
a categorized prefix. Requirement 7 and 15: a node-limited search writes a record
and exits 1, and that record verifies. Requirements 9-11: a freshly produced
record verifies; a model whose coefficient changed under an unchanged `model_id`
is refused on the fingerprint; and a mutated outcome, objective, dual bound,
forfeiture flag and each of the five counters are each detected individually, so
no field is nominally compared and actually ignored. Requirement 12: a record
differing only in `elapsed_ms` verifies. Requirement 13: a forfeited record that
verifies still reports forfeiture and is not reported as proven. Requirement 14:
a configuration naming an extension policy is refused as unsupported.
Requirements 15-18: the exit mapping, the stderr categories, absence of partial
output, and the 16 MiB boundary. Requirement 19: an absent measurement is omitted
rather than null. Requirement 20: the committed example validates under the JSON
Schema, and a document the schema rejects is rejected by the Rust parser too.

Native-dependent tests report an explicit skip when the pinned library is absent,
so a missing build is never counted as coverage. The complete
`bash tools/check.sh` gate with native acceptance covered is required before this
slice is complete.

## Open Questions

Whether verification should **tolerate** a changed backend version is unresolved.
A divergence now carries a note when the library, revision or compiler differs, so
a reader can distinguish "another build produced this" from "this result is
wrong". That is explanation only: the divergence still fails, and the ten compared
fields are unchanged. Deciding that a version mismatch makes divergence
acceptable, or gating verification on the version, would change the meaning of
agreement and therefore requires a new record version and its own decision
record. Nothing here authorizes it.

Cross-host reproducibility is untested. Floating-point behavior and library
builds may differ between hosts, and nothing here establishes that a record
produced on one machine verifies on another. Verification is currently evidence
about one host over time.

The local registry, the Python SDK, comparative experiment execution, checkpoint
restart and progress streaming are named exclusions with no contract yet. Their
recorded deferrals are in [known failures](../../state/known-failures.md).
