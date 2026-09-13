# Testing Strategy

Purpose: distinguish correctness, compatibility, performance, and development
process evidence. Scope: all milestones.

| Layer | Contract and planned coverage |
| --- | --- |
| Unit | Parsing, arithmetic, domain invariants, recurrence, backend statuses |
| Property | Feasibility preservation, permutations, serialization, seeded behavior |
| Exhaustive | Tiny assignments and permutations against independent enumeration |
| Differential | Standalone HiGHS; SCIP when available; independent schedule evaluator |
| Integration | CLI/SDK, cancellation, limits, artifact creation, extension rejection |
| GPU | CPU equivalence, overflow, selection, cancellation, device recovery |
| Regression | Minimized reproduction of every discovered defect |
| Performance | Criterion microbenchmarks and complete manifest-driven runs |
| Agent development | Task state, spec links, documentation, provenance validation |

M0 executes inventory parsing and process-level lease tests through
[cargo integration tests](../../crates/optimizer-cli/tests/cli.rs), and schema
negative cases through [artifact tests](../../tests/integration/test_artifacts.py).
All tests identify externally observable contracts. GPU leasing is tested with
simulated jobs and interoperability with util-linux flock.

M1 adds [core contracts](../../crates/optimizer-core/tests/contracts.rs) for
independent objective/violation recomputation, integer/binary domains, sparse
indexing, canonical JSON, explicit tolerances and numerical error handling, plus
[CLI contracts](../../crates/optimizer-cli/tests/model.rs). The dense integer oracle
checks 18,522 candidates across small continuous/integer/binary models; generated
tests use fixed enumeration without random seeds. Minimized parser regressions
and infeasible, unbounded, degenerate, poorly scaled and overflow-prone model
fixtures are retained in tests/. Fixtures do not establish solver classifications.

Original-variable reconstruction after transformations and CPU/GPU agreement remain
gated on later capabilities. Transformations are not implemented.

C6 fills the GPU row above, and the form its agreement evidence takes is unusual
enough to state here. The batched schedule evaluator is integer, so agreement with
[the recurrence](../../crates/optimizer-schedule/src/evaluate.rs) is asserted as
equality at tolerance exactly zero rather than within a tolerance, and determinism
follows from the arithmetic rather than from launch configuration. The LP backend has
neither property: its arithmetic is inexact, so agreement is within the caller's
tolerances and determinism is a property of a reduction order the specification
fixes. The two must not be tested as though they were the same thing.

Two anti-vacuity rules apply specifically to device tests. A fallback test must
assert that the fallback actually fired, because a device path that was never
attempted trivially agrees with the CPU path it did not replace. And a crossover
measurement must show the device losing at the smallest instance size; a report in
which the device wins everywhere is evidence the measurement excluded transfers, not
evidence the device is fast. Device-dependent tests report an explicit skip when no
device or code object is present, exactly as native-dependent tests do.

C5 fills the flow-shop recurrence and permutation-validity rows above; its coverage
is described at the end of this document.

C2 adds [search contracts](../../crates/optimizer-solver/tests/executive.rs) and
[native end-to-end acceptance](../../crates/optimizer-highs/tests/executive.rs).
The search contracts run entirely on test backends: an exact vertex-enumeration
LP solver written independently for the tests, and a scripted backend that
returns each termination in turn. That keeps the bound-validity and forfeiture
rules covered when HiGHS is absent, and it demonstrates the executive is
backend-neutral. Correctness is established by comparing 192 tiny discrete
models against brute-force enumeration of the entire assignment space, over a
fixed grid with no randomness. The native test drives the real executive over
the pinned library and compares against independent subset enumeration; it
reports an explicit skip when the library is absent.

A relaxation limit must be shown to prune nothing and to forfeit the proof
claim. Termination must not depend on backend correctness: a backend returning
solutions outside the node it was given must forfeit rather than loop.

C3 adds [extension runtime contracts](../../crates/optimizer-extension/tests/contracts.rs)
and [independent extension acceptance](../../crates/optimizer-extension-examples/tests/acceptance.rs).
The runtime contracts need no executive, so version negotiation, counted
budgets and panic containment stay covered independently of any search. The
acceptance suite lives in the examples crate, which depends on the published
extension and core APIs and takes the executive only as a test dependency, so
"an independently authored extension runs without engine-internal changes" is
established by the workspace build rather than asserted.

The central C3 assertion is negative: for every deliberately hostile extension,
the outcome, proven optimum, dual bound, forfeiture state and prune counters
must equal the extension-free run's over a fixed model grid, which itself agrees
with brute-force enumeration. Those comparisons use unlimited budgets on
purpose, because an adviser that spends a node budget badly changes exploration
quality rather than correctness. An empty extension policy must reproduce the
extension-free record exactly apart from elapsed time. A hostile adviser that
always names an integral variable must terminate, which is requirement 12a's
hazard arriving from a second untrusted source.

C4 adds [run surface contracts](../../crates/optimizer-cli/tests/search.rs),
[record contracts](../../crates/optimizer-experiment/tests/run.rs) and
[schema contracts](../../tests/integration/test_run_records.py). Reproducibility
is established by re-execution rather than asserted in prose: the surface tests
produce a record, re-run it and compare. The load-bearing assertions are the
negative ones, because a verifier that cannot fail establishes nothing. A model
whose coefficient changed under an unchanged `model_id` must be refused on its
fingerprint before any search runs, and each of the ten compared fields must be
shown to fail when it alone is mutated, so no field can be nominally compared and
actually ignored. A record differing only in elapsed time must still verify,
which fixes that measurement as diagnostic rather than contractual. A forfeited
search that verifies must still report forfeiture, so agreement cannot launder a
claim C2 declined to make. The embedded SHA-256 is checked against the FIPS 180-4
vectors and independently against Python's `hashlib` over the committed
documents, so an agreement between two implementations is verified rather than
assumed.

One gap the Rust suites cannot close by construction: each produces its record
moments earlier in the same process, so none tests that a record outlives its
author. The gate therefore re-executes the *committed* example record against the
current build through
[verify_committed_record.py](../../tools/verify_committed_record.py), and requires
the two negative directions there too, because a verifier that cannot fail
establishes nothing about the one that passed.

C1 adds [solve contract](../../crates/optimizer-core/tests/solve.rs),
[backend acceptance](../../crates/optimizer-highs/tests/backend.rs),
[differential](../../crates/optimizer-highs/tests/differential.rs),
[solve CLI](../../crates/optimizer-cli/tests/solve.rs) and
[solve schema](../../tests/integration/test_solve_artifacts.py) contracts. The
differential layer drives the standalone HiGHS executable, built from the same
pinned source, as a separate process and fails on disagreement rather than
deferring to the adapter. Native-only tests report an explicit skip when the
library is absent, so a missing build is never counted as coverage.

Every backend status must have an explicit test. Limits and numerical failures
must never become proven optimality. Performance tests are separate from
correctness tests. Tiny fixtures belong in Git; large datasets require download
scripts, checksums, source versions, and license records. A suite reproduced by a
published generator instead records the generator, seed and parameters per
instance and commits the generated documents with checksums, as
[the benchmark protocol](../benchmarks/protocol.md) now states.

C5 adds [flow-shop contracts](../../crates/optimizer-schedule/tests/contracts.rs),
[native scheduling acceptance](../../crates/optimizer-highs/tests/schedule.rs),
[CLI contracts](../../crates/optimizer-cli/tests/schedule.rs) and
[manifest provenance](../../tests/integration/test_flow_shop_manifest.py). The
schedule crate takes no solver dependency at all, not even for tests, so the
recurrence stays independent of any search and the search-driven assertions live in
optimizer-highs for the same reason the C2 ones do. Its load-bearing assertion is
the exhaustive one: over a fixed grid of
tiny instances with no randomness, the minimum makespan found by enumerating every
permutation must equal the optimum the executive proves on the encoded model, with
the grid's size asserted so it cannot silently shrink. That comparison is what
detects drift between the two computations of makespan the slice deliberately
maintains, and it compares both against enumeration rather than against each other,
so a shared error cannot hide.

The scheduling suites need three guards the earlier capabilities' lessons already
identified. A test asserting that branching occurred must check the explored-node
count first, because an encoded model whose relaxation happens to be integral makes
the assertion vacuous, which is the C3 lesson arriving from a third source. A
producer-independence test must confirm the producer was actually invoked rather
than assume it. And the generator must be asserted against a committed fixture
holding its source's own published reference instance, so "reproduces the
literature" is checked rather than described.

Requirement 26 makes an omission part of the contract: no scheduling test may
assert a runtime, a solution quality or a comparison against a published bound. A
limited search's incumbent is asserted feasible, never optimal.

C8 adds [registry contracts](../../crates/optimizer-registry/tests/contracts.rs),
[conformance CLI contracts](../../crates/optimizer-cli/tests/registry.rs) and
[registry schema contracts](../../tests/integration/test_registry.py). Its
load-bearing cases are refusals, because a registry that could not reject a wrong
claim would be a list of names and its license, authority, determinism and
promotion fields would be decorative. Each refusal is asserted in its own
`ErrorKind` category, so a single catch-all rejection cannot stand in for the
specific rule under test. The refusals that can be checked against the provider's
own construction counter are — an unmet data requirement and a gpu hardware
requirement, both of which must be refused before anything is built. The
declaration-mismatch paths deliberately cannot be: resolution has to construct an
extension and call `declare` in order to discover that its declaration disagrees
with the entry, so the counter is non-zero there by design and requirement 14's
"MUST NOT construct" is narrower in practice than it reads. That gap is recorded
in [known failures](../../state/known-failures.md) rather than asserted away.

The conformance suite is exercised through `optimizer registry check` rather than
described. The committed [conformance record](../../examples/conformance-record-v1.json)
is regenerated by that command and compared byte for byte, which is what makes it
evidence: `examples/extension-registry-v1.json` promotes `flow-shop-neh` by citing
that file's SHA-256, so without a regeneration test the promotion would be
cryptographically checkable but never empirically re-checked, and a producer that
regressed would keep citing a passing record. The suite's own invariance
comparison is unit-tested against each field it compares, because SPEC-0004's
containment means no extension reachable through the host can move those fields —
a broken comparison would otherwise look exactly like a conforming extension.

Two C8 checks are deliberately outside the Rust suites. The
[gate's committed-record step](../../tools/verify_committed_record.py) re-executes a
registry-backed scheduling record committed at an earlier revision, because every
Rust re-execution test builds its record moments earlier in the same process and so
cannot establish that a record outlives its author. And two registry rules are
cross-field — that an entry's authority follows from its category, and that no two
entries share an identity — so a JSON Schema cannot express them; the integration
tests pair each against the Rust parser rather than against the schema alone.

A conformance record is contract evidence and not a measurement. No C8 test asserts
that a registered extension improved a search, and the record carries no timing
field that could be read that way.
