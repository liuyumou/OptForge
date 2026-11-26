# Pricing LP research

An isolated implementation study of [Strongly Polynomial Linear Programming, November 24, 2026](https://github.com/openai/math/blob/main/preprints/Strongly-polynomial-linear-programming-November-24-2026/paper.pdf).

The practical solver returns independently checked original-model certificates.
The reference code connects Sections 3–6, with component tests for its mathematical
operations. **A complete literal reference run has not been validated:** its
parameters and recursive tree exceed the admitted resource limits. The practical
variant has no strongly polynomial complexity claim.

See the [implementation plan](../../docs/plans/lp-sp-pricing.md) and
[measured evaluation](../../docs/benchmarks/lp-sp-pricing.md). The frozen held-out
confirmation is complete: 246 attempts and six capacity refusals across 252 slots.

## Implemented paths

- `paper_reference`: exact minors; symbolic affine log comparisons; online
  common-scale compression with LLL and restart invalidation; compressed
  calibration; bounded rational ellipsoid feasibility; implicit expert cells,
  exact counts and moments; lexicographic market optimization; recursive wealth;
  sequential circuit restrictions rebuilt from the original space; and the
  feasibility, recession and strict primal–dual optimality reductions.
- `certified_acceleration`: the same reference structure, with exactly checked
  GPU label proposals and exact ellipsoid fallback. It retains literal parameter
  admission and does not silently switch to the practical algorithm.
- `practical`: direct input-height calibration, 6N singleton experts plus
  4096 seeded four-slot experts, up to three adaptive epochs and 65536 extras,
  and at most 1024 queries. Pool expansion preserves the seeded prefix and
  explicitly starts new uniform wealth. Exact restricted-cone witnesses permit
  early recovery without claiming a minimal circuit.

Every mode distinguishes mathematical certificates, deadlines, resource refusals
and implementation errors. Original-model primal/dual, Farkas and improving-ray
checks are implemented independently in
[the verifier](../../tools/lp_sp_pricing_verify.py).

## CPU implementations

The practical market has an exact integer implementation. A signed-network
double cover solves its flow dual; exact allocation mass, signed coordinate
balance and objective equality certify the market optimum. Residual-potential
constraints recover lexicographic prices. The original exact cutting-plane
oracle remains available for differential tests and unsupported native ranges.
The [market derivation](market-notes.md) explains the flow equivalence and checks.
The native flow implementation uses bounded 128-bit capacities and checked
64-bit costs; it is not the reference bit-polynomial market oracle.

Auxiliary LPs use a persistent exact GMP tableau, sharing a feasible basis across
objectives. A positive target stops on a checked witness; a negative target needs
an optimal dual certificate. Native rational elimination, sparse exact proof
products and a proved isotropic-displacement bound reduce geometry/checking cost.
The Python exact implementation remains an independent differential oracle.

The CPU native library currently targets the pinned installed Linux x86-64 GMP
6.2.1 ABI. Its small C declarations avoid a system package installation. Builds,
runtime identity, malformed inputs, differential tests and ASan/UBSan are recorded.
Changing that runtime requires new admission.

## GPU implementation

The newer **synchronized wave candidate** is implemented in
[`gpu_wave.py`](python/sp_pricing/gpu_wave.py),
[`batch_wave.cu`](native/batch_wave.cu), and
[`proof_interval.cpp`](native/proof_interval.cpp). It overlaps CUDA initialization
with CPU geometry/market work, retains a solve-scoped allocation arena, advances
all signed auxiliary objectives through shared checkpoints, and reuses matrix
coefficients across four right-hand sides. Native buffers feed a rigorous
interval checker directly; uncertain decisions use the existing exact GMP path.
The [interval argument](interval-notes.md) documents the acceptance guarantees.

Its isolated entry point is `tools/lp_sp_pricing_wave_run.py MODEL OUTPUT`.
The backend is installed only in that child process; the CPU and preceding lean
paths remain available as controls. Use the study reservation wrapper and fresh
identities for builds, admission and evaluations. The build explicitly targets
the admitted sm_120 GPU; another architecture requires a new build and admission.
See the [preparation and synchronized-search evaluation](../../docs/benchmarks/lp-sp-pricing-wave.md).

The final opt-in startup policy is
[`OpportunisticWaveBackend`](python/sp_pricing/gpu_wave_policy.py), exposed by
`tools/lp_sp_pricing_wave_policy_run.py MODEL OUTPUT`. It lets the existing exact
CPU oracle handle a query when CUDA initialization is still in progress, then
uses synchronized GPU searches when ready. It neither waits at the first query
nor suppresses initialization failures; teardown includes any unfinished startup.
The [separate fresh policy comparison](../../docs/benchmarks/lp-sp-pricing-wave-policy.md)
retains both the earlier wave policy and CPU as controls.

The [million-scale experiments](../../docs/benchmarks/lp-sp-pricing-million.md)
separately test original LPs with one million nonzeros and auxiliary matrices
with one million coefficient positions. Their historical candidate retains its
explicit geometry limits; auxiliary throughput is not a claim of million-scale
complete-solve capability.

The subsequent opt-in **compact candidate** uses sparse exact factors and an
implicit orthogonal complement, lazy CPU fallback tableaus, tiled GPU products
and interval checks, and bounded synchronized batches. Two upload slots stream
matrices beyond the bounded device cache; one producer and one host checker
overlap preparation/checking with GPU advancement. Its entry point is
`tools/lp_sp_pricing_compact_run.py MODEL OUTPUT`, with `--cpu` and `--serial`
controls, through the same resource reservation wrapper. See the
[compact implementation and measurements](../../docs/benchmarks/lp-sp-pricing-compact.md).
It handles an auxiliary space with 128 million coefficient positions using
4000 stored positive-factor entries. The three original million-nonzero LPs
pass dimension admission but reach the CPU geometry deadline before a query
in that compact-only cohort. Existing defaults are unchanged.

The subsequent **native geometry candidate** adds sparse GMP elimination,
exact GPU modular proofs for full spaces, and numerical factor proposals checked
against the original LP with exact bounded integer arithmetic. A proved original
certificate can return before pricing construction. This is explicitly reported
as certified presolve, with no paper-algorithm completion claim. The entry point
is `tools/lp_sp_pricing_geometry_run.py MODEL OUTPUT`; `--no-presolve` retains
pricing construction and `--cpu` disables GPU paths. The
[fresh million-scale COPT comparison](../../docs/benchmarks/lp-sp-pricing-geometry.md)
includes input preparation, factorization, GPU initialization if used, teardown
and independent endpoint checks in complete time.

The opt-in **lean candidate** is implemented in
[`gpu_lean.py`](python/sp_pricing/gpu_lean.py),
[`batch_optimized.cu`](native/batch_optimized.cu), and
[`proof.cpp`](native/proof.cpp). It uses FP64 only, diagonal PDHG steps,
reusable GPU buffers, continued state, active-target compaction, and a short
stratified pilot before exact CPU fallback. Small matrices use a persistent
kernel; larger matrices use four row warps per block and CUDA graph replay.
Native GMP checks return compact exact label decisions and avoid duplicate
matrix products and unnecessary dual checks. Full intermediate witnesses are
omitted from its runtime trace; final original-model certificates remain.
The CPU comparison control uses the same compact trace policy.

Build with `tools/lp_sp_pricing_gpu_opt.py build <fresh-identity>` through the
study reservation wrapper, then run the source-bound CPU/GPU admission in
`tools/lp_sp_pricing_gpu_opt_quality.py`. The minimal candidate entry point is
`tools/lp_sp_pricing_gpu_lean_run.py MODEL OUTPUT --library LIBRARY`;
`--cpu` selects the exact CPU control. These entry points also require a fresh
reservation. See the [follow-up measurements](../../docs/benchmarks/lp-sp-pricing-gpu.md).
This is a practical acceleration path, with no strongly polynomial guarantee.

The archived implementation below remains a differential baseline. Its arithmetic
modes are excluded from the lean candidate hot path.

A Rust/CUDA context shares one calibrated matrix and transpose across independent
auxiliary states. Dense and CSR products support widths 1, 8, 32 and 64. Both
signed slots can be searched in the same batch. Exact opposite-slot witnesses
can establish negative labels; unresolved targets are compacted, escalated to
FP64 and then sent to the exact CPU oracle.

Arithmetic modes are FP64, FP32 component counts 2/4/8 and simulated E2M1
component counts 1/2/4. Input upload and accumulation are FP64. Additional
components improve proposal arithmetic; they do not supply arbitrary precision.
FP4 storage is unpacked and these kernels use CUDA cores, so packed-FP4 storage
savings and tensor-core performance are not claimed.

GPU outputs carry no acceptance authority. Exact dyadic host calculations check
primal feasibility and box-support dual upper bounds against the rational basis.
Preparation, device iterations, transfers and checking are recorded separately.
Recursive outer proposals have sequential wealth dependencies; batching applies
to independent auxiliary searches.

Final GPU admission covers 224 configurations and all four CUDA sanitizers.
Both CPU native components pass ASan/UBSan. The 35 mathematical tests include
the actual grouped-market/ellipsoid path, symbolic compression, native
differential checks and circuit recovery.

## Evaluation and resources

The independent study allocation is 240000 CPU / 30000 GPU seconds, with
phase caps, four CPU slots, 128 GiB host and 80 GiB owned GPU memory. GPU jobs
require a fresh 30-second idle observation and exact ownership supervision.
All failures retain their full charges. Historical experiment identities,
numerical sources and public solver defaults remain unchanged.

The separate-seed 21-case development ladder selects CPU: both paths certify
14 cases, while capped total cost is 88.3 seconds on CPU and 114.7 seconds with
GPU proposals. These are development measurements, not held-out superiority.

The frozen confirmation contains 28 original LPs across seven families,
three solvers and three rotated repetitions: 252 slots. Baselines are unchanged
image-v11 and COPT scale-off GPU PDLP. Each gets its specified native/process
window. The same independent original-model 1e-9 checker evaluates every endpoint;
the exact rational tier is reported separately. Ratios require jointly timely
accepted endpoints and include complete process/verification costs.

The candidate has six timely strict certificates, image-v11 has three, and COPT
has none under the independent checker. The one jointly certified model has
three repetitions: candidate complete cost is about 1.31 times image-v11's.
Broader end-to-end superiority is not established. Vendor optimal status is
reported separately from the checker's ability to obtain a finite rigorous bound.

Six family reservations failed during output-directory setup before starting
an LP. Their full charges remain. Recovery keeps all original inputs, numerical
sources and windows, but executes those CPU candidates and GPU baselines in
separate blocks to fit the remaining phase limits. The cross-lane ordering
deviation is explicit, so timing comparisons are descriptive.

The two proposed original billion-nonzero cases fail explicit-basis capacity
admission before generation. Sparse original input does not prevent dense
null-space fill. Their unsupported rows remain in the report.

## Reproducing components

The subsequent [larger-scale evaluation](../../docs/benchmarks/lp-sp-pricing-scale.md)
uses two seeds per family at 4–16 million nonzeros, a 120-second native allowance,
and independent full-matrix arbitrary-precision certificate checks. Its isolated
entry point is `tools/lp_sp_pricing_scale_run.py MODEL OUTPUT --seconds 120`.
The frozen campaign uses `tools/lp_sp_pricing_scale_experiment.py` through the
source-bound `tools/lp_sp_pricing_scale_budget.py` adapter. Historical identities
must not be rerun; its fixed two-hour allocation is not an open-ended launch permit.
The new certificate boundary checks integer ranges before conversion and verifies
cached coefficients against the original model. Numerical geometry, GPU kernels
and the earlier measured sources remain unchanged.
The report also separates a fresh 300-second, partial third-seed supplement and
a common endpoint-reconstruction diagnostic. The latter applies identical
bounded rounding and independent exact acceptance to all available candidate
and COPT endpoints, without rerunning an LP or changing the raw results.

Use fresh reservation identities, within the remaining study allocation.
From the repository root, CPU tests can be run with:

```sh
python3 -B tools/lp_sp_pricing_budget.py --id fresh-component-tests --phase reference --seconds 180 --host-gib 8 -- python3 -B -m unittest discover -s tests/integration -p test_lp_sp_pricing.py
```

The isolated native build entry points are
[market build](../../tools/lp_sp_pricing_market_build.py),
[exact auxiliary build](../../tools/lp_sp_pricing_auxiliary_build.py), and
[Rust/CUDA build](../../tools/lp_sp_pricing_native.py).
Run them through the same reservation wrapper. Full historical evidence and the
retained baseline binaries are host-specific; the repository does not claim a
portable replay of those private artifacts.
