# SPEC-0022: Solver-neutral LP baseline contracts

Status: CPU contract implemented under the user's GPUP-BASELINE-SPEC request,
2026-11-10; solver execution and proposed resource allocations are not authorized.
Scope: optional development-only project/cuOpt/COPT comparisons, not a runtime backend.
Owner: experiment tooling and numerical backend.
Introduced: GPUP-BASELINE-SPEC, following ADR-0047.
Last reviewed commit: 396bd0e2ea095f1d038dfa862bb31f29a61e0d68.
Supersedes: none; historical SPEC-0013/0019 artifacts keep their meaning.
Implementation: [CPU contract validator](../../tools/lp_baseline_contract.py).
Tests: [focused contract tests](../../tests/integration/test_lp_baseline_contract.py).
Protocol: [baseline proposal](../benchmarks/lp-external-baseline-v1.md).

## Purpose and authority

Compare total cost to an independently accepted LP answer using identical original
models and a declared resource envelope. A solver's status, residual or objective
is an observation, not a certificate. This slice supplies canonical input,
solver-neutral endpoint and proposal schemas plus CPU validation. The vendor
adapters, generalized Rust checker bridge, supervisor and numerical study belong
to GPUP-BASELINE. Passing JSON validation never authorizes or certifies a solve.

## Requirements

### Original model and canonical arrays

1. Input MUST be a continuous version-1 original model with unique u32 variable
   and row IDs, finite binary64 coefficients and objective offset, and correctly
   oriented finite or infinite bounds. Duplicate terms MUST be rejected before
   sparse-library conversion, never summed. Unknown IDs and reversed bounds refuse.
2. The [canonical model schema](../../schemas/lp-baseline-model-v1.schema.json)
   MUST bind the exact original bytes by SHA-256 and preserve objective sense,
   offset, coefficient values, explicit signed zeros and original ID order.
   Sorted IDs define array order. Canonical values are binary64; integers that
   cannot be represented exactly as binary64 refuse rather than silently round.
3. Canonical CSC MUST have n+1 monotone pointers starting at zero and ending at
   nnz; row indices MUST be strictly increasing within each column and in range.
   Objective/variable arrays have n entries; row bounds have m entries. Empty
   models, rows and columns are legal input shapes, not evidence of useful work.
4. A null lower bound means negative infinity; a null upper bound means positive
   infinity. Numeric NaN/infinity and duplicate JSON keys MUST be rejected.
   Vendor infinity sentinels MUST NOT replace a finite original bound; unsupported
   finite ranges or coefficient filtering MUST refuse with a reason.
5. The adapter MUST preserve the original arrays independently of solver scaling
   and presolve. CSC-to-CSR conversion may permute storage only, preserving value
   bits. No default clipping, coefficient dropping, duplicate coalescing or repair
   is allowed. Ranged rows SHOULD use the native lower/upper APIs on both vendors.

### Endpoint and checker boundary

6. Each [endpoint envelope](../../schemas/lp-baseline-endpoint-v1.schema.json) MUST
   bind original/canonical model hashes, configuration and proposal hashes, adapter
   and environment identities, original IDs, actual primal/row-dual vectors or
   explicit absence, and optional native reduced costs. Missing data are null,
   never fabricated zeros or a vector from a previous solve.
7. The row dual MUST be in original units and normalized to minimization:
   sigma=+1 for minimization and -1 for maximization; normalized cost is sigma*c.
   Positive row dual selects a finite lower row bound; negative selects upper.
   If a solver returns original-sense duals, multiply by sigma exactly once.
   Native reduced costs are diagnostic and MUST NOT replace recomputation.
8. Presolved solutions MUST be postsolved to every original variable and row
   before export. Any row split or transform needs an explicit versioned mapping
   and independent admission; the initial design avoids external row splitting.
9. Original-model candidate evaluation, `optimizer_lp::certify` and `assess_gap`
   MUST remain the numerical authority. Recompute z=sigma*c-A^T*y with the
   retained outward arithmetic. Preserve its row-dual repair, unbounded-variable
   refusal, objective offset and conservative gap enclosure. A checker refusal
   is not proof that the original LP is infeasible or unbounded.
10. The primary quality policy MUST use original-model absolute and relative
    tolerances both 1e-9, including the existing feasibility and outward gap
    predicates. It MUST NOT be replaced by an absolute-gap-only test, rounded
    objective subtraction or matching vendor parameter names. Lower quality tiers
    are outside this version.
11. Transport outcome, native status and checker outcome MUST be distinct. A
    native `optimal` row without accepted checker evidence is uncertified. Native
    infeasible/unbounded claims remain unverified diagnostic statuses in this
    version, which supplies no Farkas/ray verifier. A finite endpoint returned at
    a native limit can certify if it completes within the outer deadline and the
    checker accepts it.
12. GPUP-BASELINE MUST add a new solver-neutral Rust bridge reusing the existing
    mathematical routines. The current `external-certify` v1/v2 readers accept
    COPT-specific identities; a cuOpt witness MUST NOT be relabeled as COPT. The
    new envelope is not directly accepted by those historical CLI readers.
13. An accepted checker receipt MUST bind the actual original model, witness,
    checker source/binary, tolerances and assessment. Its bytes/hash and numerical
    content MUST be verified before reporting certified timing. This slice's
    validator checks envelope structure/consistency only, not receipt mathematics.

### Execution, provenance and timing

14. Requested GPU execution MUST be distinguished from confirmed CPU, GPU or
    unknown execution. A visible GPU, package import, requested method or missing
    native log MUST NOT establish actual GPU use. GPU claims require pinned UUID
    and execution evidence. Unconfirmed execution remains in coverage, outside
    the confirmed GPU subset; no silent fallback or substitute solver is allowed.
15. Native settings MUST be explicit for method, precision, tolerance, threads,
    time limit, presolve and crossover where supported. Record effective settings,
    defaults left in use, unsupported seed/work controls and actual winning
    algorithm. COPT precision is opaque; its GPU label is not a low-precision claim.
16. Primary latency MUST run from immediately before launching a fresh worker to
    worker exit with durable endpoint and independent checker output, including
    conversion, library/context/license setup, solve, extraction, certification,
    serialization and teardown. Queue/lease waiting is separately recorded.
17. Native solve duration and optional warm-process latency MUST be separately
    labeled. Warm runs may reuse immutable setup only; they require fresh solver
    state and certificate, with no previous solution/basis unless a separate
    repeated-solve cohort explicitly permits it. This proposal allocates no warm
    measurements, profiles or hardware-counter study.
18. Coarse host phase clocks MAY be collected without extra synchronization in
    primary trials. Native log timestamps are not kernel phase timings. Overlapping
    native/host durations MUST NOT be added. Missing metrics MUST remain null with
    an entry in limitations; zero denotes an observed zero.
19. Every trial MUST bind a frozen source snapshot, executable/library/environment
    hashes, original model and setting hashes, hardware/driver, CPU affinity,
    lease, process outcome, partial artifacts and resource receipt. Hashes identify
    exact bytes; paths MUST remain inside the declared artifact root, including
    symlink resolution. The design proposal is not a frozen execution manifest.

### Comparison, resources and failures

20. The [proposal schema](../../schemas/lp-baseline-proposal-v1.schema.json) MUST
    keep `execution_authorized=false`. The CPU tool MUST NOT launch vendor solvers,
    create a device context, reserve historical funds or accept an execution flag.
21. GPUP-BASELINE MUST first pass new conversion/checker mapping tests and bounded
    vendor readback/solve acceptance. Require useful nonzero iteration work and
    certified nontrivial endpoints for each forced PDLP lane before its timing
    admission. Trivial host-only success cannot substitute. An unavailable lane
    stays in the planned denominator and receives no fabricated timing.
22. A future execution manifest MUST freeze source/library/checker hashes, exact
    GPU UUID and CPU set, accepted resource authority, model identities, effective
    settings, complete job list and deterministic order before release. Missing
    license, incompatible GPU stack, unsupported export or unproved containment
    MUST refuse the affected release without automatic dependency changes.
23. Resource reservations MUST cover work, certification and cleanup before launch.
    The proposal uses four CPUs and conservative four-times-job-wall CPU charging,
    one GPU job at a time, explicit phase caps and no automatic borrowing/retry.
    Failed/unsettled reservations retain their full charge. Actual overruns are
    recorded fully and close further execution. Historical journals are immutable.
24. Correctness/provenance/resource gate failure MUST stop dependent phases.
    Planned numerical refusal or timeout cells in an admitted screening study are
    results, not successful samples; they remain recorded and charged. A new
    execution identity/protocol is required to change settings or retry.
25. Screening MUST use three repetitions per model/configuration, deterministically
    ordered within model/repetition blocks. Report certification and GPU-confirmation
    coverage against all planned cells, plus per-model paired medians and bootstrap
    uncertainty. Failed pairs MUST remain visible rather than be omitted from a
    claimed aggregate win. Finalist/held-out studies need at least ten repetitions
    under a separate accepted protocol and remain outside this slice.
26. Related models MUST remain in one split. This proposal uses development only;
    it MUST NOT inspect the held-out manifest. General commercial competitiveness,
    real-world coverage or a precision preset MUST NOT be inferred from this
    generated screening corpus. Additional real sparse data require source/license,
    conversion and group/hash admission before a separate cohort is frozen.

## Compatibility and error handling

All three schemas reject unknown fields. Schema versions are separate from the
existing external-witness v1/v2 namespaces. A new mandatory field, normalization
or mathematical policy needs a new schema/decision, not edits to old evidence.
The validator returns nonzero for malformed/ambiguous input, inconsistent IDs,
hashes, dimensions, outcomes or budgets. It reports `contract_valid`, never
`solver_accepted`. Duplicate-key/nonfinite/path-substitution failures are fatal.
Original numerical libraries, APIs, artifacts and settings are unchanged here.

## Acceptance and remaining implementation

The focused CPU tests cover malformed JSON; min/max, signed zeros, free/fixed and
ranged bounds; duplicate/unknown terms; CSC shape/order; endpoint identity and
missing duals; optimal-status versus certification; GPU evidence; deterministic
ordering; exact two-phase arithmetic and refusal of execution authorization.
They use synthetic records labeled as fixtures, not vendor results.

Run `python3 -m unittest discover -s tests/integration -p test_lp_baseline_contract.py`.
Run `python3 tools/lp_baseline_contract.py proposal benchmarks/configs/lp-external-baseline-proposal-v1.json --verify-artifacts`
for CPU-only proposal validation. Full solver, Rust bridge, real postsolve-sign
checks, GPU compatibility and supervisory resource acceptance remain GPUP-BASELINE
work. Gurobi is unavailable and not a prerequisite. GPUP-8 remains incomplete and
GPUP-9 remains gated.

Examples: [canonical input](../../examples/lp-baseline-model-v1.json) derived from
the existing tiny original model, and an explicitly [synthetic unavailable endpoint](../../examples/lp-baseline-endpoint-v1.synthetic.json).
The latter deliberately contains no candidate, solver run, certificate or timing.
Validate it with `python3 tools/lp_baseline_contract.py endpoint examples/lp-baseline-endpoint-v1.synthetic.json --model examples/lp-baseline-model-v1.json`.
