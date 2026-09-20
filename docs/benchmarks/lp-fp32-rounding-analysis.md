# FP32 Rounding: Failure Mechanisms and Exact-Representation Candidates

Status: reproduced CPU investigation, 2026-09-16; GPUP-5B under
[ADR-0021](../decisions/ADR-0021-exact-scaling-components.md). The completed
[latency diagnosis](lp-fp32-slowdown-diagnosis.md), its report bytes and archived
GPU evidence remain unchanged. This note adds interpretation and reproducible
CPU feasibility evidence, not GPU speed or convergence results.

## Where rounding occurs

| Stage | Existing GPUP-5 behavior |
| --- | --- |
| Preconditioning | Ruiz and Pock-Chambolle scales, scaled coefficients, bounds and objective are computed in FP64. Non-dyadic scales can make originally exact FP32 coefficients inexact in FP32. |
| Matrix storage | Convert the canonical scaled matrix once, nearest-even, then derive the transpose by permutation of the same converted values. |
| Products | FP32 mode narrows vector operands and explicitly rounds the FP32 multiplication; widening the result cannot recover the discarded bits. |
| Accumulation | FP32 mode rounds each lane addition and each fixed-tree addition. The current generic implementation also uses conversions and double-width shuffle values. |
| Working state | FP32 mode rounds state stores, including the anchored update. Host restoration/restart and continuation after correction explicitly round the working copy. |
| Retained FP64 | Master data, controller, objectives, bounds, vector-update arithmetic and original-model host validation/certification remain FP64. |

Nearest-even is deterministic but is not exact arithmetic. Gradual underflow
preserves representable subnormals; it cannot represent a product smaller than the
available range. The observed product-loss guard (bit 4) reports nonzero operands
producing zero. Disabling it would conceal that event, not fix matrix bias.

## Why more iterations may not help

For the stored scaled operator, write `A32 = A64 + E`. At a fixed vector `x`,
the activity difference is `E x`; it remains even if the iteration residual for
`A32` approaches zero. Original-model feasibility also accounts for the original
bounds and unscaling, so the saved-witness analysis evaluates those explicitly
using exact rational arithmetic, rather than treating a represented residual as
a certificate. Scaled-bound rounding is not separately modeled by that diagnostic.

The archived irregular-2048 storage run performs 50000 proposals versus 1600 for
precision FP64 (31.25 times), and dense_block-1024 performs 50000 versus 1800
(27.78 times). Both storage runs fail certification despite similar or cheaper
updates. Timing coverage falls from 27/36 to 12/36, and to 6/36 with FP32 state.
Row 805 of irregular-2048 violates its original allowance by 34.2 times while
meeting the implied represented-operator allowance; dense_block-1024 row 798
exceeds its allowance by 15.8 times. These are direct observations of material
operator bias. Some other failed endpoints also have large represented residuals:
not every failure has been shown to be at a rounding floor.

A simple illustration is the constraint `x = 1`, scaled by the stored FP64 value
of `1/3`. Its FP32 coefficient is 0.3333333432674408 while the FP64 right-hand side
is 0.3333333333333333. The represented solution is 0.9999999701976784, with original
error approximately 2.9802321610539195e-8. Iterating more accurately on that
represented equality cannot recover the lost coefficient.

Fixed correction recomputes one final update from the saved pre-step state;
it does not restore the preceding 31 updates. The archived six corrections on
irregular-2048 add about 3.291 ms plus transfer/synchronization costs, without
recovering study coverage. Executor overhead is separate: generic guarded kernels,
six launches per update and frequent readback remain even in the precision-FP64
control. Hardware counters were denied; bandwidth/cache/occupancy explanations
remain hypotheses, not measurements.

## Reproduced CPU evidence

Run `python3 tools/analyze_lp_rounding.py`. Its immutable output is
`artifacts/gpup5b-rounding-v1/analysis.json`, with input/operator/witness/tool hashes,
seed 17002, exact rational row shifts and the illustrative equality. It reads only
the twelve development operators and archived storage-FP32 witnesses.

| Representation of scaled FP64 coefficients | Exact coefficients / 166292 | Maximum absolute coefficient error |
| --- | ---: | ---: |
| One FP32 component | 18 | 2.922716180187024e-8 |
| Two FP32 components | 33430 | 8.881784197001252e-16 |
| Three FP32 components | 166292 | 0 |

All 166292 original coefficients are already exactly FP32. Rounding the existing
diagonals to nearest powers of two in logarithmic distance preserves FP32
representability of all tested transformed matrix coefficients. The exponent
choice uses an integer significand-square comparison, not platform logarithms.
This result concerns coefficients; transformed bounds/objective data and the
changed preconditioner's convergence still need their own checks.

At the archived irregular-2048 row-805 witness, the matrix-induced activity shift
relative to the FP64 scaled operator is approximately -2.98923970091906e-7 with one
component, +6.1208901718542175e-15 with two, and exactly zero with three.

A separate sample spans the finite FP64 exponent range, with signed zeros,
smallest subnormals, smallest normals, maximum finite values and seeded random
bit patterns. Normalize each operand into `m * 2^e`, then repeatedly round the
mantissa and its residual to FP32. Three components reconstruct all 10006 sampled
values exactly. All 45027 sampled component cross-products equal an FP32 rounded
product plus its CPU-emulated FMA residual, evaluated exactly as rational numbers.
These are sampled CPU observations, not device measurements or a proof by testing.

## What can be bypassed or replaced

Exact FP32 storage after power-of-two scaling, or retaining the original matrix
and applying the two diagonal scales separately in FP64, can avoid the initial
scaled-matrix FP32 conversion loss on this corpus. The former changes the
preconditioner; the latter changes floating-point evaluation order. Both therefore
need matched controls. Neither bypasses rounding in subsequent arithmetic.

Three FP32 components plus exponent metadata can preserve all FP64 input bits.
Two components are a labeled approximation. Exact input reconstruction does not
make component products or sums exact: all cross-terms and their rounding errors
need treatment. Raw three-component storage already costs 12 bytes versus 8 for
FP64, before exponents or indices; splitting both operands requires nine
cross-products. Their costs can exceed hardware arithmetic savings.

[FMA and IEEE arithmetic](https://docs.nvidia.com/cuda/floating-point/index.html)
and [error-free product/sum transforms](https://www.tuhh.de/ti3/paper/rump/OgRuOi04a.pdf)
provide established building blocks, with range assumptions that must be checked.
No claim of a newly invented arithmetic method is made. Dense matrix-multiply
acceleration, including [Ozaki extensions](https://arxiv.org/abs/2511.13778), does
not establish sparse single-vector speed: packing, metadata, padding and extra
operations must be charged on this workload.

Changing deterministic rounding direction changes the perturbation, rather than
restoring discarded bits. Stochastic rounding can reduce certain systematic
accumulation effects; one randomized matrix conversion still freezes one perturbed
operator. Resampling requires consistent transpose values and replay semantics,
and does not by itself guarantee the original 1e-9 target. These alternatives
and their prerequisites are recorded in the [candidate register](../plans/lp-precision-candidates.md).

The subsequent GPU investigation is recorded separately in the
[GPUP-5B report](lp-exact-components-gpup5b.md). Its results do not retroactively
turn the CPU samples above into device measurements or change the archived diagnosis.
