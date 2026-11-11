# SPEC-0030: Coupled FP4 recovery integration

Status: complete bounded integration; admission passes, latency retention fails
Owner: numerical backend and CUDA runtime
Date: 2026-11-11
Decision: [ADR-0062](../decisions/ADR-0062-fp4-coupled-integration.md)
Prerequisites: [SPEC-0029](SPEC-0029-fp4-recovery-policy.md), [SPEC-0028](SPEC-0028-fp4-fast.md)

Delivery: [complete results and accounting](../benchmarks/lp-fp4-integrate.md).

## Numerical and execution contract

Implement a separate, bounded research solver for coupled LPs of at most 128 rows
and columns. One CTA owns a complete LP; each warp owns 32 output coordinates.
Tensor contractions visit all input tiles, including cross-tile terms, in fixed
order. Shared-memory barriers separate primal and dual phases. A single RHS uses
MMA columns for component planes. Exact-zero matrix planes may be skipped; no
nonzero product is discarded. Prepared matrix fragments, the original operator,
all five state vectors, scales and complete checkpoint storage remain resident.
This domain is an explicit bound, not a general large sparse LP implementation.

The recurrence extends the admitted pilot's unweighted PDHG map to general bounds:
`u=Pi_X(x+tau*(A^T*y-c))`, `bar=2*u-x`,
`v=y-sigma*A*bar-Pi_[-sigma*U,-sigma*L](y-sigma*A*bar)`.
Use fixed `tau=sigma=2^-shift`, with shift at least one and selected so
`tau*sigma*||A||_1*||A||_inf <= 3/4`. There is no Halpern blend or adaptive native
restart in this version; both anchor vectors are nevertheless retained exactly
for complete rollback/conversion. Native, FP8, FP16 and FP4 controls use the same
recurrence, steps, original model, bounds and audit schedule. Native is a matched
FP64 arithmetic control, not a claim of equivalence to the supported production
solver's adaptive controller. The supported native solver stays unchanged.

FP4, FP8 and FP16 use local FP32 pairs and admitted instruction helpers derived
from the immutable pilot/FAST sources. No ordinary update reconstructs a full
FP64 state. Row/column bounds and objective coefficients use local pairs; their
representation errors are explicitly charged. Infinity is permitted only for
absent bounds; padding has zero values and no model semantics.

Apply SPEC-0029's operational policy: audits by 200 updates, at most one submitted
32-update chunk, explicit complete rollback, monotone 2 -> 4 -> 8 -> native
recovery and original-model checking at the declared 1e-7/1e-9 tier. FP8/FP16
controls hand off directly to native on refusal. Logical accepted progress may
roll back; physical updates, deadline and all costs never do. Device and host
state bind model, settings, policy, generation and precision. A reused service
must reject stale generations and preserve physical work across precision loads.
Cancellation stops and restores without starting a new solve. A failed conversion
must restore and select native, with no further FP4 attempt. Failed native work
is terminal. The new word-packed checkpoint transport covers all five vectors,
all codes/scales and exact exported values, plus controller progress and identities;
it is a transport adapter to SPEC-0029, not a redefinition of the old checkpoints.

## Local arithmetic evidence and final authority

Report seven terms: operator approximation, instruction, combination, scalar,
projection, encoding and discarded pairs. Original-A and transpose row-sum
errors are recomputed from decoded matrix storage. Local re-encoding error is
measured before/after each encoding, including the extrapolated vector and its
subsequent product. Local roundoff estimates include pair combination/scalars,
with forward/transpose amplification within the update. Compare the conservative
common normalized allowance to both x/y scales from the last audit.

Instruction error may be recorded as a **device-observed zero estimate only**
after the pinned image passes independent actual-instruction/product differential
checks. It is not a general arithmetic theorem. Pair roundoff estimates and
observed encoding errors are likewise operational, not a global trajectory
bound. Failure to admit the actual arithmetic blocks the device path. Projection
comparisons use the combined pair and declared bound representation, never
componentwise clipping; unsupported/ambiguous comparisons require recovery.

The independent checker calls unchanged original-model feasibility evaluation,
conservative dual-bound construction and gap assessment. A separate CPU process (one-shot or persistent checker service) receives only original model and exported endpoint, never approximate A or
device residuals. Explicit absolute/relative target tolerances are both 1e-7 or
both 1e-9; public defaults do not change. Preserve objective direction/offsets,
finite-bound refusal, repair and nonfinite rules. Hash model, endpoint and checker
image. CPU tests must distinguish a valid 1e-7 endpoint from a strict refusal.

## Admission, grid and performance

Freeze eight exact model generators before execution: coupled equality,
inequality, ranged/one-sided, fixed/active bounds, ill-scaled coupling, irregular
33-tail, rich 65-dimension and an intentional infinite-bound refusal. Nonzero
starts, active bounds, cross-tile coupling, maximization and objective offsets
are present. Known constructed KKT endpoints admit the checker; they are never
used to initialize a numerical solve. The negative family remains visible.

CPU contracts/build and checker admission precede device primitives. Compare
actual coupled products/steps against an independent original-A recurrence,
plus exact rollback and stale/cancellation/budget tests. Run memcheck, racecheck,
initcheck and synccheck on changed paths before the formal grid. Preserve every
failed development source, image, output and full reservation. Routine versioned
implementation repairs are authorized; scientific cell identities are frozen
only after admission and are never retried automatically.

Formal integration: eight families x six lanes (native, FP8x4, FP16x2, FP4 starts
2/4/8) x two final tiers = 96 fixed-work diagnostic cells, targeting 600 physical
updates with original-model observations at or before each 200 accepted updates.
Record all useful FP4 work, precision changes, early safety stops, and independently
checked endpoints. A diagnostic continues after recording a certificate; a solve
stops at its first actually checked certificate. The intentional bound-refusal
family does not become certified by completing its updates.

Performance development may optimize the coupled arithmetic, context/model
reuse, audit/export/checker delivery and checkpoint lifecycle. Compare unchanged
endpoints where the numerical path is intended to stay identical. Freeze a
separate paired cold solve grid after correctness/safety admission; report all
individual timings, same-tier medians, uncertainty, coverage and every added
cost. Prepared reuse and cold time remain distinct. GPU event time is not complete
solve latency; source hashing, preparation, contexts, transport, audits, recovery,
export and independent checking count. A negative result remains a valid measured
outcome, not an unsupported preset. TENSOR2 still needs its own complete-cost
admission and resource package; GPUP-8 stays incomplete and GPUP-9 gated.

Prepared solves reuse only the CUDA context/module and independent checker process.
`finish` destroys all per-solve numerical buffers, counters and controller state;
the next load starts from the original nonzero initial state. Every command binds
a monotone solve identity as well as a generation. Lifetime physical work and the
external reservation never reset. Cancelled services are terminal. Measure startup
separately and disclose its amortization; prepared solve time is not cold time.
The native control uses exact CSR/CSC traversal, skipping structural zero terms.
The CUDA image excludes unrelated legacy kernel exports. All scalar and matrix
source preparation still counts. Final checking may reuse an exact endpoint's
same-tier receipt; it cannot infer an earlier unobserved certification time.

After all admission, freeze a separate 576-cell performance grid: eight models,
six lanes, two final tiers, three repetitions, cold and prepared lifecycles.
Cold cells are fresh Python/Rust/checker processes timed from outside their
startup through exit. Prepared cells keep context/checker processes with fresh
numerical state; their separately measured startup is also reported. Each solve
has 10000 physical updates and a 30-second controller deadline (40-second outer
cold deadline). Record limits and all coverage failures. Use fixed seeded ordering,
bootstrap model medians for descriptive uncertainty, and no automatic cell retry.
The eight diagnostic models and 96 cells retain the 600-update protocol.

## Independent resources

The current user request authorizes a new implementation/performance package:
96000 CPU seconds, 14400 GPU seconds. CPU phases: implementation 24000 including
512 conservative preparation; native software acceptance 16000; device acceptance
24000; bounded study/optimization 24000; reporting 6400; cleanup 1600. GPU phases:
acceptance 6000, study 8400. Four CPU slots, one shared lease on the pinned SM120
device, 16 GiB sampled host RSS, 12 GiB device buffers; unchanged in-container
supervisor. Full jobs must fit before launch; failed/unsettled jobs retain full
charges. Snapshot new CUDA headers as well as kernels, Rust sources and tools.
No historical allocation transfers or old numerical retries. Commit locally after
delivery; no push/publication is requested.
