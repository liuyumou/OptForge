# SPEC-0002: HiGHS Backend Contract

Status: accepted
Scope: CPU LP/MILP backend and solve CLI
Owner: numerical backend
Introduced: M2
Last reviewed commit: 9b42b62
Supersedes: none
Implementation: pending
Tests: pending

## Purpose

Solve original M1 linear models with pinned HiGHS and validate extracted
candidates independently. Native backend termination is numerical evidence,
not an exact-arithmetic certificate. Owned branch-and-bound belongs to M4.

## Terminology

A backend status describes native termination. A candidate is an assignment in
original variable IDs. A validated incumbent passes SPEC-0001 with the explicitly
recorded tolerances. A basis is an opaque, model-bound LP warm start.

## Requirements

1. The backend MUST use HiGHS 1.11.0 with 32-bit HighsInt and CPU-only builds.
2. Safe Rust MUST own native handles, keep them private, destroy them exactly
   once, and reject dimensions or indices that exceed the native integer range.
3. Loading MUST preserve original IDs, objective sense/offset and ranged rows.
   Binary bounds MUST intersect with [0,1]. Unsupported native numeric ranges
   MUST fail explicitly; coefficients MUST NOT be silently dropped by HiGHS.
4. Every native model status MUST map explicitly, including ambiguous
   unbounded-or-infeasible and unknown states. Native API errors MUST remain errors.
5. Solve configuration MUST explicitly supply seed, time limit, iteration/node
   limits and numerical tolerances. Native solves MUST use one CPU thread.
6. Cancellation MUST be cooperative through atomic state and native interrupt
   callbacks. Pre-cancelled solves MUST return interrupted without native work.
   Cancellation latency is bounded by native callback availability, not wall time.
7. Extracted candidates MUST pass original-model validation before publication.
   Recomputed objective and violations MUST accompany accepted incumbents.
   Invalid native output MUST return a numerical failure, never optimality.
8. All warnings, native status and explicit configuration MUST remain in solve
   records. Time/iteration/node limits MUST NOT imply proof completion.
9. Warm starts MUST support validated complete candidates and model-bound LP
   bases. Wrong-model, malformed or unsupported starts MUST fail explicitly.
10. The CLI MUST preserve native OS paths, bound JSON files to 16 MiB, reject
    unknown/duplicate arguments and return categorized I/O and argument failures.
11. Records MUST be versioned, serializable without nonfinite numbers and retain
    enough configuration and backend provenance to repeat the solve.

## Interfaces

The safe backend accepts an immutable Model, explicit SolveOptions, a shared
CancellationToken, and an optional candidate or basis. Solve records distinguish
termination from candidate feasibility and retain native model status, HiGHS
version, elapsed time, warnings and original-model validation. LP basis state
is opaque and tied to the exact canonical model, not only its caller-supplied ID.

The model solve CLI accepts --model and --config paths plus optional
--candidate. Solve configuration is a strict versioned JSON object. A successful
record is emitted atomically at the application level through fallible writes;
bytes delivered before a stream failure cannot be retracted. Exit 0 means a
completed solve outcome, 1 means a limit or unresolved outcome, 130 means
interruption, and 2 means an argument, I/O, unsupported or backend/numerical error.

## State and Invariants

M1 models and tolerance semantics remain unchanged. Native integrality and bound
tolerances are explicitly configured separately from original-model validation.
The native small-matrix threshold is fixed and input below it is rejected rather
than silently altered. Finite native infinity/cost limits are checked before load.
Basis ownership and callback state outlive their native uses; callbacks cannot
unwind. Native global scheduler use is serialized within the wrapper.

Optimal means HiGHS reported optimal under recorded numerical settings and any
primal solution passed M1 checks; it MUST NOT be described as an exact certificate.
Empty models require original constraint evaluation rather than trusting native
model-empty classification. Unboundedness is backend evidence, not a feasible
incumbent. Nonfinite bound/gap information is represented as absent, not JSON null
substituted for an allegedly finite measurement.

## Errors and Recovery

Construction, native API, unsupported input, numerical validation and output
errors are categorized. Failed operations leave no published successful record.
Drop releases native resources after every return path. A later solve uses fresh
native state; no failed model is reused implicitly.

## Compatibility and Versioning

M1 documents stay at version 1. New solve configuration and result documents have
their own version 1. Bootstrap experiment schemas stay unchanged; M6 will define
the enclosing experiment format and migration. No Python SDK or CUDA dependency.

## Security and Resource Limits

Linux x86-64 is supported. Four workers may build native code; each solve uses
one thread. The API is synchronous with explicit limits and cooperative
cancellation. Rust callers own memory budgets; CLI experiment workers in M6 will
enforce process memory limits. Source downloads are checksum verified and cached
outside tracked source. Raw handles cannot cross the FFI boundary.

## Acceptance Tests

Requirements 1-3: ABI assertions, original-ID matrix conversion, binary bounds,
native numeric boundaries, empty/infeasible/unbounded/poorly-scaled fixtures.
Requirements 4-8: every native status, standalone LP/MILP comparisons, independent
candidate checks, time/iteration/node limits and cancellation. Requirement 9:
candidate and basis round trips plus wrong-model rejection. Requirements 10-11:
CLI strict inputs, output failures, deterministic configuration round trips and
reproducible records. Repeated lifecycle tests run under available sanitizers.
All CPU contracts and bash tools/check.sh are required before M2 completion.

## Open Questions

None for this bounded contract. Native proof rays, dual certificates and safe
owned-search pruning require the M4 contract before their public introduction.
