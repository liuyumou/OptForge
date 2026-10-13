# ADR-0036: Full expansion state admission

Status: accepted admission-refusal decision, 2026-10-13; full controller/device behavior is not accepted
Owner: numerical backend
Introduced: GPUP-STATE
Last reviewed commit: bootstrap
Superseded by: none

## Context

The user accepted a full expansion controller rather than a hybrid FP64 scalar
controller. GPUP-REP supplies correctly rounded 64-significand-bit reference
primitives; GPUP-EXEC supplies bounded exact binary64 dots with FP64 state. Neither
accepts complete expansion state, logarithms/exponentials, or device primitives
for a full controller. Numerical ambiguity blocks that affected implementation.

## Decision and admission sequence

The requested target is `lp-state-v1`, with matched FP64, compensated scaled 24/24-bit
pairs and 24/24/16-bit Expansion64. Expansion64 retains the accepted normal range
[-1022,1023], gradual underflow through 2^-1085, signed-zero semantics and
nearest-even primitive rounding. Pair state uses 48 significand bits and gradual
underflow through 2^-1069, with a separately identified error contract. Each live
vector, scale and controller scalar is inventoried; no FP64 reconstruction is
permitted in an expansion iteration/control path. Preparation and final host
certification retain their explicitly declared native arithmetic.

Accept CPU proof/oracle/resource admission before runtime/device implementation.
Logarithms and exponentials need conservative range-reduced intervals at 128,
192 and 256 working bits. An ambiguous rounding cell refuses; native fallback
is not a recovery path. A demonstrated numerical or resource admission failure
may complete this investigation with a reproducible counterexample and reasoned
refusal. This does not prove that every alternative expansion algorithm is impossible.

The proposed sparse accumulator is signed 320-bit, with at most 65536 products
and a 128-bit product-base-exponent window. 64-by-64-bit products are below 2^128;
alignment and length give partial magnitudes below 2^272, within 319 magnitude
bits. The magnitude bound is below 2^272, requiring **at most** 272 bits, not
fewer than 272 bits; the selected width remains sufficient. Canonical binary64
coefficients and one transpose permutation remain.
Exact reduction and scalar primitive admission are separate obligations.

Stable formulas are piecewise support-function projection on the negated row
range and norms without premature square overflow. Port initialization, norm/step
estimation, Halpern updates, KKT indicators, weight gains and restart decisions to
the declared arithmetic. Snapshots bind every live field and identity; restoration
invalidates caches without reducing physical work or extending deadlines. Coupled
primal/dual updates commit atomically; publication is a charged binary64 conversion
and fresh original-model assessment. Existing schedules, methods and records remain.

## Resource authority

The user allocates 3600 GPU seconds under ADR-0035's existing cumulative ceiling
21602.574545061: timing 2300 screening, profiles 450 ablations, acceptance 850
repeatability. Phase ceilings remain baseline 1800, screening 9500, ablations
7650, repeatability 4450 and finalists 9000, and the overall cap remains 28800.
Preserve 17635.432015338 seconds, 16366 events and ledger SHA-256
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b.
Unused allowance does not admit a job before the numerical and task gates.

The intended development grid is the eight GPUP-EXEC models, four configurations
(tuned FP64, matched FP64, compensated pair, Expansion64), three repetitions and
twelve 200-proposal profiles. Inherited deadlines/tolerances/seeds stay fixed.
Worst-case timing/profile reservations are 2256/432 seconds, respectively.
Acceptance initially reserves three 120-second jobs and four 90-second sanitizer
jobs, totaling 762 seconds with deadline+6 overhead. Every real job requires the
shared host lease on GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48. Failed identities
remain retained and charged; primary attempts are not retried.

CPU cap is 21600 seconds/four jobs, host RSS 8 GiB, device resident/preparation
peak 1/2 GiB and new artifacts 32 GiB. Shapes are at most 65536 rows/columns and
2^23 nonzeros. Expansion kernels require at most 128 registers/thread, zero
compiler spills and accounted explicit scratch. Compilation is provisioning,
not an ordinary build dependency. No new runtime dependency or unsafe boundary
is authorized.

## Acceptance

Independent rational/integer fixtures, proof and layout receipts precede the
full pinned-native gate. Every admitted device family additionally requires
instruction audit, CPU/device differential, same-device replay and four scoped
sanitizers. The frozen report retains coverage, original residuals, total fresh
latency, work, conversion/control costs, memory and failures. A refusal report
must identify the exact failed gate and retain its counterexample; it cannot
claim runtime/device acceptance or measured solve performance.

## Admitted result and rejected construction

Close this bounded investigation with the [resource-refusal report](../benchmarks/lp-expansion-state-gpup-state.md).
CPU integer/rational validation checks 192 restoring integer operations, 270
full-range FMA cases, 64 unprojected primal/Halpern graphs and 48 transcendental
cases. This admits those CPU validation tools and their explicit refusals only.
It does not admit a complete controller, pair codec, snapshot API or runtime ABI.

The 320-bit row accumulator does not establish full-range scalar FMA. Exact
alignment of the full-range product and addend can require 3194 magnitude bits
for Expansion64 and 3162 for the 48-bit pair. The tested first construction
retains them in a signed 3200-bit bin. NVCC 13.0.88 for sm_120 uses 255 registers,
a 152-byte stack and 296/152 spill-store/load bytes for **both** full-FMA kernels.
This fails the accepted 128-register/zero-spill gate. Bounded integer and
unprojected update probes fit at 62/76 registers with no spills; those partial
passes cannot promote the complete required family.

The source, host oracle fixture, CPU executable, compiled image and actual
instruction/resource receipts are frozen and independently reverified. No CUDA
context was loaded and no kernel executed. No comparative study was admitted:
all 96 timing and 12 profile cells remain planned/unexecuted. The task GPU charge
is zero and the historical ledger stays exact.

This rejects the direct full-bin construction, not every algorithm for either
format. Symbolic guard/sticky algorithms and explicit global scratch could avoid
register retention; they need a separately bounded proof, implementation and
traffic/resource test. A narrowed scalar window would be a new numerical subset.
Neither such alternative nor a hybrid FP64 controller is substituted here.
GPUP-REFINE is the next priority and needs its own accepted contract/allocation.
