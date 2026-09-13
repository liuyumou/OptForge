# ADR-0006: Reproducibility by Re-execution

Status: accepted
Owner: research infrastructure
Introduced: C4
Last reviewed commit: f8d6091
Supersedes: none; ADR-0001 through ADR-0005 remain in force

## Context

C1, C2 and C3 are complete, and each produces a record that carries enough
configuration to repeat what it describes. `SolveRecord` and `SearchRecord` both
embed their full options, every budget is explicit with no defaults, and
`Model::fingerprint` identifies exact canonical model bytes. None of that is
checked against a second execution: no code re-runs a record and compares.

The evidence that closes Stage 3 in
[the implementation plan](../../implementation-plan.md) is that "a run remains
reproducible from pinned revisions and records after its originating agent is
unavailable." Today that is an assertion with no test behind it. The research
plan makes the same requirement structural: a configuration should remain
reproducible when its originating agent or model is no longer available, and the
accumulated records are supposed to be the evidence collection that later
capabilities retrieve from.

There is a second gap. `optimizer-solver` is not a dependency of any non-test
crate, so the executive and the extension host have no agent-independent surface
at all. Everything C2 and C3 established is reachable only from Rust test code.

The decision this record fixes is what "reproducible" means operationally, before
a registry, an SDK or a comparative experiment runner is built on top of it.

## Decision

Implement [SPEC-0005](../specifications/SPEC-0005-run-surface.md): reproducibility
is established by re-executing a run from its record and comparing the two search
records field by field. The record is the unit of reproducibility. A run record
carries provenance plus the verbatim search record, and `optimizer verify` re-runs
using only the record's embedded configuration and the model it names.

Verification reads no result from the record as an input to the run it performs.
It reads configuration, runs, and then compares. This is the whole point: a
verifier that fed the recorded outcome into the run it was checking would confirm
its own input.

Divergence names the field. Verification compares the outcome, the recomputed
objective, the dual bound, the gap, the forfeiture state and all five counters,
and reports which one differs. It deliberately does not diagnose why. A changed
engine, a rebuilt backend library, altered model bytes and different host
floating-point behavior all present as a named divergence, and distinguishing
them is a separate contract this record does not write.

Elapsed time is recorded and excluded from agreement. It is a measurement of the
host, not a property of the search, and including it would make every
verification fail. Recording it anyway keeps it available for diagnosis while
refusing to make it a contract.

A record is bound to model bytes by fingerprint, not by `model_id`. C1 already
made this decision for LP bases, where a basis is rejected when the model's data
changed even though its identity did not. Verification inherits that rule rather
than inventing a weaker one: a record whose model was edited under an unchanged
identifier is refused before any search runs.

Agreement is not a mathematical claim. It is evidence of determinism.
Verification cannot upgrade a forfeited search into a proven one, cannot turn a
limit into optimality, and adds no authority to any record. Two runs agreeing
that a search forfeited its proof claim is exactly as much of a proof as one run
saying so.

A run that reached a limit or was interrupted still writes its record. An
unfinished search is a fact about a run, and discarding its record would leave the
caller unable to see what a budget bought. Only a run that could not start writes
nothing, because there was no run to describe.

A configuration naming an extension policy is refused as unsupported rather than
run without the extension. The executive's registry parameter is an in-memory
slice for one search, and this surface has no mechanism to load an extension into
it. Running anyway would produce a record describing a search the caller did not
request, which is the class of quiet substitution this project's records exist to
prevent. The refusal marks the seam the deferred registry fills.

Provenance field names are taken from SPEC-0007's experiment result rather than
chosen fresh, so the two provenance shapes in the repository cannot drift apart.

The Python SDK is not implemented and is deferred with a stated blocker: pyo3
expands to unsafe code, the workspace forbids it, and ADR-0003 permits unsafe only
inside optimizer-highs. An SDK therefore requires a decision record amending
ADR-0003, which no current requirement justifies. The local registry is deferred
to its own specification.

Existing seeds, tolerances, thresholds, splits and solver defaults do not change.
This surface adds no numerical behavior and no mathematical authority; it observes
and records what the executive already decided.

## Alternatives

Storing a hash of the result and comparing hashes would be cheaper and is
rejected because it cannot survive a legitimate change: any backend upgrade or
added record field breaks every stored hash identically, with no indication of
which property actually changed. Field comparison degrades usefully where a hash
degrades uselessly.

Trusting the stored record and validating only its schema would make verification
instant and would establish nothing. A record is a claim about an execution;
checking that it is well-formed does not check that it is true, and the whole
requirement is about a run whose author is gone.

A live session or daemon protocol, where a client attaches to a running search and
retrieves results, is the conventional design for progress and cancellation. It is
rejected as the reproducibility mechanism because it fails the stated requirement
outright: it needs the originating process to still exist.

Comparing on `model_id` instead of the fingerprint would let a caller verify a
record against a corrected model and get agreement, which is precisely the silent
mismatch C1 already rejected for bases.

Including elapsed time in agreement would be a stricter-looking rule and is
rejected as unusable: it fails on every host under every load, and a check that
always fails is deleted rather than obeyed.

Adding a progress or telemetry hook to the executive in this slice would serve the
"inspect progress" capability the research plan names, and is deferred because it
is new public search surface, needs its own contract for what an observer may see
and when, and is not required by reproducibility. The current path is synchronous
by design.

## Consequences

Verification costs a second full search under the record's own budgets. A record
with no budget therefore implies an unbounded verification, which the caller can
see in the record before starting.

Agreement is evidence about one host over time. Cross-host reproducibility is not
established: floating-point behavior and library builds may differ between
machines, and nothing here tests that. This is stated as an open question rather
than implied by the word reproducible.

Verification assumes the pinned native library is unchanged. A rebuilt or upgraded
HiGHS that changes a node count produces a named divergence. That divergence now
carries a note when the library, revision or compiler differs from the record's,
which tells a reader the engine also changed without excusing the disagreement:
the comparison itself is untouched and the run still fails. Deciding that such a
mismatch is tolerable would change what agreement means and needs its own decision
record.

Restart from a checkpoint remains unimplemented. `Checkpoint` is defined and
serialized by C2, no entry point consumes one, and this surface does not add one,
so a long search still cannot be resumed.

The CLI gains its first dependencies on optimizer-solver and
optimizer-experiment, which makes the executive reachable from the binary and
gives optimizer-experiment its first types after being a schema-embedding stub
since M0.

No performance claim is made or measured. Whether the executive is fast is not
this record's question, and a run record's elapsed time is explicitly not a
benchmark result.

## Implementation and Tests

Implementation in [optimizer-experiment](../../crates/optimizer-experiment/src/lib.rs)
and [optimizer-cli](../../crates/optimizer-cli/src/main.rs) over the
[search executive](../../crates/optimizer-solver/src/lib.rs) and the
[run record schema](../../schemas/run-record-v2.schema.json), verified through the
[gate](../../tools/check.sh). No behavior is implemented by this decision record.
Acceptance evidence is recorded in [active task](../../state/active-task.md); this
slice is not complete until its full gate passes with native acceptance covered
and verification is shown to fail on a mutated record.
