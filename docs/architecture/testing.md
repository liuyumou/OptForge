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

M1-M5 must add objective recomputation, reconstruction of original variables,
integer/binary domains, sparse indexing, deterministic serialization and seeding,
flow-shop recurrence, permutation validity, overflow rejection, unsupported models,
and CPU/GPU evaluator agreement. They are **not covered by M0**.

Every backend status must have an explicit test. Limits and numerical failures
must never become proven optimality. Performance tests are separate from
correctness tests. Tiny fixtures belong in Git; large datasets require download
scripts, checksums, source versions, and license records.
