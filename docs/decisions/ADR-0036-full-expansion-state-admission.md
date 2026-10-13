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

## Original admitted result and rejected construction

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

## PR 19 review experiment (2026-10-13)

The user's request to challenge and improve the negative result authorizes one
bounded CPU/compile-only alternative, separately identified from the frozen
full-bin construction. It changes no format, rounding, register/spill threshold,
solver behavior or GPU allocation. Use at most 7200 CPU seconds, four build jobs,
8 GiB host RSS and 4 GiB new artifacts; execute no device workload.

Test a compact FMA that aligns the exact 128-bit product and 64-bit addend at
`max(product_unit, addend_unit) - 160`. Each retained magnitude fits 288 bits;
one extra carry fits in the existing 320-bit container. At most one operand
needs a right shift. Replace its discarded nonzero tail by a low odd bit.
If this is inexact, the other term is divisible by 2^160 and the shifted term
is below 2^127, so cancellation cannot lower the sum's leading bit below 159.
For precision at most 64, final rounding therefore discards at least 96 bits
(more at gradual underflow). The integer surrogate is odd and differs from the
exact sum by less than one intermediate unit. Every nearest-even boundary is
an even integer on this grid, so that perturbation cannot cross a rounding
boundary, including ties, overflow and underflow. If no tail is discarded the
sum is exact. Like-signed zeros and exact cancellation retain the original
signed-zero contract. Zero terms do not select the alignment exponent.

Before resource compilation, compare both constructions against independently
rounded exact Fractions over an additional deterministic seed-17019 boundary corpus:
midpoints on both sides, sign/cancellation, subnormal and overflow transitions,
and alignment cutoffs. Keep the original seed-17004 fixture byte-identical.
Use undefined-behavior checks on the host construction. Freeze and independently
verify the new source, fixture, binary, image and complete instruction/resource
receipts. Retain every failure. An alternative scalar resource pass establishes
neither device correctness nor a full primitive family/controller; it challenges
only the sufficiency of the original stopping reason. No runtime or subsequent
GPUP task is started here.

Review result: both compact variants fit at 40 registers and zero stack/spills;
both original variants retain the 255-register/spill refusal. All 5900 additional
cases per construction, host UBSan checks and the original 270 FMA cases pass.
The [review report](../benchmarks/lp-expansion-state-gpup-state.md#pr-19-challenge-and-evidence-repairs)
records the independent freeze, stronger evidence verifier and full pinned-native
acceptance. The scalar obstruction is therefore construction-specific and does
not remain a reason to reject all full-range FMA. Full device/controller behavior
remains unaccepted and GPUP-REFINE retains its separate contract/allocation gate.

## Authorized primitive device extension (2026-10-13)

The user explicitly authorizes device evaluation and publication in PR 19 after
the compact CPU proof/resource pass. This supersedes the earlier review's
zero-GPU restriction only for this bounded scalar experiment. No full controller,
state/replay API, solver performance study or change of next_ready_task follows.

Use an isolated safe Rust diagnostic example through optimizer-cuda-sys's
existing driver boundary and the shared supervised lease on
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48. Ordinary Cargo builds require no toolkit.
Retain the original refused construction; never launch its kernels. Audit the
actual differential and benchmark images before execution under the unchanged
128-register/zero-spill/no-native-FP64 gate. Bound allocations to 64 MiB and
initialize outputs/guards, with guard outcomes and untouched overflow outputs
checked explicitly. Device inputs are canonical finite 48/64-bit operands.

Freeze two fresh-process correctness attempts. Each checks all 6170 historical
and supplementary cases, block sizes 64/128/256, and zero/partial-block launches
at counts 0/1/31/32/33/127/128/129. Repeated launches must match bitwise and both
processes must match independent oracle expectations. Run memcheck, racecheck,
initcheck and synccheck over the same correctness paths and bounded instances of
the benchmark paths. Every failed or interrupted identity remains visible.

The descriptive timing roster has two precisions, three patterns (exact unit
increment, far-tail sign alternation, and exact cancellation), two shapes
(one dependent chain of 16385 operations and 65536 independent chains of 129
operations), and three fresh-process repetitions: 36 attempts. Cycle counts
describe dependent-chain work including control; synchronized launch wall time
includes submission and synchronization. Report input/output transfers, context,
module, allocation and total process/lease costs separately. Timings do not imply
FP64 equivalence, a speedup over the refused implementation, or a solver benefit.
Inputs/results are exactly specified dyadics; independent expected endpoints
are verified before timing is admitted. One warmup precedes one measured launch
per fresh attempt, with both checked; no result-dependent tuning or retries.
Odd iteration counts make alternating/cancelling endpoints differ from their
initial values; generated-code inspection must also retain the dynamic loop.

Reserve at most 1100 GPU seconds of the existing GPUP-STATE allocation: 600
screening timing and 500 repeatability acceptance (inside 2300/850). Two 30-second
correctness jobs, four 90-second sanitizer jobs and 36 ten-second timings reserve
1032 seconds including deadline+6 per job. CPU cap 14400 seconds/four jobs, RSS
8 GiB and new artifacts 4 GiB. Campaign and phase ceilings are unchanged.
Every execution requires an exact-source full native gate and frozen executable,
source, image, protocol, requests and independent fixtures. Append to the existing
canonical ledger, preserving its 16366-event prefix and all historical identities;
charge actual lease time or conservative crash reservations. Report device
correctness and descriptive primitive measurements separately from open complete
state/controller obligations, then publish the implementation and evidence in
the existing PR 19 without merging it.

### Explicit alternate-device cohort (2026-10-13)

The first gpup-state-device-v1 attempt was blocked by external activity before
child/context launch, charged 3.002084480 seconds, and retained without retry;
its other 41 cells remain unexecuted. The user explicitly requested using another
idle GPU if available, otherwise publishing the incomplete device result.
Discovery found both RTX 5090s occupied and the sm_120 RTX PRO 6000 Blackwell
Server Edition GPU-6721b13a-30f9-83ec-dace-ba2d9738556f idle. Admit a separately
frozen gpup-state-device-v2 cohort on that device, retaining the same arithmetic,
roster, compiler options and acceptance gates. This is an explicitly authorized
device change before any numerical endpoint or timing, not outcome selection.
Keep every v1 receipt and do not retry its identities. Use the same shared host
lock; no simultaneous devices. Timings describe the PRO 6000 only and cannot be
substituted for prior RTX 5090 results or treated as cross-device equivalence.

The v2 cap is 1096 seconds: 496 acceptance and 600 timing. Adding the v1 charge
stays below the original 1100 total/500 acceptance/600 timing authority; the
unused fractional second is not reserved. Preserve the 16368-event prefix
SHA-256 a97630527900a1a11cfd612bd3f96d55a86c211555bb0adc7de3ab52adebfc96 and
17638.434099818 cumulative seconds, as well as all earlier prefixes. No further
cohort, automatic device fallback or retry is admitted by this amendment.

The v2 first two checks passed. Memcheck returned zero and wrote its zero-error
summary to stdout, but the verifier read only stderr and classified the receipt
as missing. A CPU-only evidence repair may inspect both captured streams, retain
the original classification, and bind a reviewed result to its raw result,
worker, endpoint and log hashes. No execution is repeated. Before continuing
unattempted cells, freeze the revised verifier source and pass its exact-source
full native gate; compare its archive against the original and permit differences
only in the verifier, its source-only tests, this decision and active task.
All executable/kernel/build/supervisor sources, corpus, protocol and compiled
artifacts must remain identical. This repairs evidence interpretation, not the
numerical result, sanitizer outcome, threshold, roster or device contract.

### Recorded device outcome

The v2 cohort completes all 42 endpoints: two ordinary checks, four scoped
sanitizers and 36 independently verified primitive timings, on the PRO 6000 only.
All six correctness processes agree over the 6170-case corpus and partial/benchmark
paths. The original v1 has one activity-blocked attempt and 41 unexecuted cells.
The memcheck classification repair retains its failed raw classification and
accepts the unchanged zero-error endpoint; no execution is repeated. The
[report](../benchmarks/lp-expansion-state-gpup-state.md#scoped-device-validation-and-primitive-costs)
records all timings, limits and exact source/repair identities. Dependent patterns
cost approximately 7928–11724 cycles/FMA; no FP64 or solver performance comparison
is established. Scalar/resource admission passes; full controller obligations remain.

Combined charge is 30.114068273 seconds: 8.460919662 acceptance and 21.653148611
timing, within all original caps. Cumulative consumption is 17665.546083611 /
21602.574545061 seconds. The 16452-event ledger SHA-256 is
24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18, preserving both
16368- and 16366-event prefixes and every historical phase ceiling. No next-task
reservation follows. Full pinned-native acceptance includes 289 Python tests.
