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

Original-variable reconstruction after transformations, deterministic solver
seeding, flow-shop recurrence, permutation validity and CPU/GPU agreement remain
gated on later capabilities. Transformations are not implemented.

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
scripts, checksums, source versions, and license records.
