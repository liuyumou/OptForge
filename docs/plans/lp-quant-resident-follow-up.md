# GPUP-7R: Resident quantized execution and matched comparison

Status: proposed, 2026-10-22; planning only, no implementation or GPU authorization
Owner: numerical backend and experiment tooling
Introduced: GPUP-7 follow-up
Last reviewed commit: bootstrap
Implementation: none; acceptance requires the proposed [ADR-0041](../decisions/ADR-0041-resident-matrix-quantization.md)
Acceptance: the staged gates and frozen comparison below

## Problem and bounded objective

The [GPUP-7 report](../benchmarks/lp-quantization-gpup7.md) establishes no useful
quantized solve benefit. Its matched FP64 control also times out on every
nontrivial timing model. Unchanged tuned FP64 solves scheduling-20x5,
irregular-2048 and irregular-32768 in median fresh-process times of approximately
0.56, 0.46 and 2.55 seconds. Quantized and matched paths hit 10/30-second deadlines.
Small-4 certifies before any update and cannot establish an arithmetic benefit.

The new path runs guards and FP64 updates on the CPU, transfers vectors for
each product and retains this machinery after full promotion. Irregular-32768
has 431993 coordinate tiles for 589482 coefficients. In the retained CPU
matched-control trace, product guards consume 36.7 of 57.6 solve-loop seconds.
All six quantized irregular trajectories promote at the first nonzero primal
product. These are CPU admission observations; incomplete GPU profiles do not
support a GPU transfer/kernel cost decomposition. The input data are in the
[retained report](../benchmarks/data/quant/report.json) and
[CPU admission](../benchmarks/data/quant/cpu-admission.json).

Answer two questions separately: can a resident executor remove the new path's
structural overhead, and do conservative, less coarse bounds admit useful
FP16/FP8 work at the existing accuracy limits? A refusal or a negative result
answers the second question. This slice does not promise a quantized winner.

Scope is one new single-solve research executor, one compact sparse layout,
one two-level guard policy and a small matched comparison. Preserve lp-quant-v1,
the tuned backend, accepted historical decisions, measured code/images, all
records and the entire ledger. There is no Tensor Core, vector quantization,
stochastic rounding, new scale policy, refinement/anchor combination, assessment
scheduling experiment, session, persistent checkpoint or supported preset.

## Proposed numerical and execution contract

These are proposed requirements for a separate lp-quant-resident-v1 interface;
they do not amend the behavior of lp-quant-v1. ADR-0041 must be accepted before
implementation. The implemented subset of SPEC-0012/0021 must then identify the
new executor, guard arithmetic, reduction trees and evidence acceptance map.

1. Preserve direct binary64 nearest-even binary16/E4M3/E5M2 conversion,
   maximum-based power-of-two scales, canonical sparse 32-by-32 coordinate tiles,
   common coefficient IDs and transpose/promotion identity. Retain original
   coefficients separately. No saturation or silent nonzero deletion is allowed.
   FP8 semantics remain pinned to the
   [CUDA 12.9 conversion specification](https://docs.nvidia.com/cuda/archive/12.9.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__FP8__MISC.html).
2. Keep primal, dual, extrapolated vectors, anchors, update arithmetic and
   numerical state in FP64. Keep their working buffers resident on the GPU.
   The host owns the existing restart/weight controller and original-model
   assessment. Reuse tuned residency, bounded submission and FP64 update
   arithmetic through an opt-in adapter without changing legacy arithmetic.
3. Retain FP32 operands/products/deterministic tile reductions for low tiles,
   FP64 inter-tile combination, and original scaled FP64 coefficients with FP64
   operands for promoted tiles. Disable contraction and FTZ. Freeze the new
   segmented reduction trees before CPU admission; identify them in evidence.
   A changed tree has its own error proof and differential tests. It is not
   asserted bitwise identical to the historical tile tree or tuned sparse tree.
4. Treat coordinate tiles as logical quantization/promotion groups. Use one
   compact segmented CSR/transpose layout, with shared coefficient IDs and
   scales; do not materialize dense 32-by-32 storage. Pack small oriented groups
   together for execution instead of allocating an entire warp to each mostly
   empty group. There is no layout search or runtime autotuning in this slice.
5. Retain separate primal/dual absolute product budgets of 1e-7 in original
   units, audit interval 32 and primal/dual absolute/relative audit tolerances
   of 1e-7. Retain fresh host certification at unchanged 1e-9 tolerances. No
   residual-only guard, sampled admission, skipped guard or relaxed budget is
   permitted in a solve. Diagnostics with guards disabled are not solve evidence.
6. Keep ADR-0040's format-independent twice-absolute-coefficient norm envelope
   and its fixed common safe step, constructed before controller creation.
   Bind operator buffers, layouts, masks, summary caches and step receipts to
   an immutable operator identity plus promotion generation. A tighter step
   policy is outside this follow-up; a bridge control exposes its cost.
7. Preserve uniform whole-operator promotion and selective promotion of every
   low tile touching a violating row/column, with the 25% coefficient cap and
   eight selective transitions. Full promotion remains sticky, with no demotion.
   A fully promoted operator skips irrelevant FP32 conversion/decode work but
   still satisfies the native product-error/range contract and audit policy.
8. Do not copy full vectors or scan full masks/summaries on the host for each
   product. Validate immutable metadata and promotion state once per generation.
   At an audit/controller/recovery boundary transfer only the state required
   for that boundary, compact guard status and declared diagnostic counters.
9. Use strict versioned settings/evidence that identify the executor, layout,
   reduction trees, guard arithmetic, operator/mask generation, norm/step policy
   and originating session. Distinguish solve, fixed-work profile and product-only
   diagnostic modes and name each work horizon's units. Record requested/executed
   precision, failure status, certification provenance and complete resource
   counters. Reject unknown fields and inconsistent/oversized counters.

## Two-level conservative guards

Replace the CPU group scan with a device admission program. This changes bound
construction and placement, not the 1e-7 budgets or original-model authority.
All preconditioning, coefficient representation, FP32 operand conversion,
multiplication, the actual reduction trees and original-unit unscaling errors
remain covered, including subnormals. No cancellation credit is inferred from a
small rounded product or residual.

Precompute outward row/column constants for a cheap global-vector envelope.
For each product compute resident vector infinity and conversion-error bounds
once, then test the output envelopes in O(rows + columns) work. These constants
must cover all group terms, arithmetic depth and underflow allowances under the
current generation. A passing envelope avoids detailed error-summary traversal.
Coarse failure is an instruction to evaluate a tighter bound, not to promote.

For outputs that fail the cheap test, accumulate a coefficient-weighted bound
while reading their sparse product data. If B* is the exact scaled original
coefficient, q its decoded low representation and vhat=RN32(v), the non-arithmetic
part of the scaled error is bounded by

~~~text
sum_j upper(abs(B*_ij - q_ij)) * abs(v_j)
    + sum_j abs(q_ij) * upper(abs(v_j - vhat_j)).
~~~

Add outward multiplication/reduction errors for the frozen tree and explicit
gradual-underflow allowances, then bound unscaling in original units. Use actual
group lengths/tree depths rather than a blanket gamma_64 for every short group.
For native entries use only the original preconditioning and FP64 arithmetic
terms with original FP64 operands. Prove both constructions independently;
neither is presumed cheaper or tighter on every input.

The detailed bound, including its own computation error, must enclose the exact
error. Device outward operations may use the pinned CUDA
[directed double intrinsics](https://docs.nvidia.com/cuda/archive/12.9.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__DOUBLE.html).
An independent integer/Fraction interpreter must model the actual directed
arithmetic program and test boundary decisions. Nonfinite bounds or exhausted
native budgets yield named refusals. A failed detailed bound drives the existing
promotion rule; it is not replaced by audit agreement.

Fuse detailed bounds/range checks with product reads where possible. Record
coarse/detailed pass counts, metadata bytes, guard work and original-unit bound
components separately. Store compact summaries; rebuild only affected generation
caches after promotion. Do not cache vector-dependent bounds across updates.

## Resident windows, audits and recovery

Submit a window of at most 32 updates, shortened at every 200-update numerical
boundary, remaining-work boundary or cancellation/deadline poll. A window keeps
state on-device and has no product-by-product host synchronization. Device
failure flags are checked before dependent FP64 projections/blends can conceal
range failures. Save the final update's pre-step state for the host audit.

The first failing product records a deterministic failed-update/orientation and
violating row/column bitmap. Subsequent dependent updates are predicated off.
FP64 vector updates also retain the range/forbidden-underflow checks on their
arithmetic intermediates before clipping or blending can conceal a failure.
At the boundary the host observes the failure, restores the complete window-start
state and promotes atomically before charged replay. No mask is changed while
an old-generation kernel is outstanding. Actual executed/rejected products,
audit updates, replay, submitted-but-predicated slots and elapsed time have
separate counters; predicated slots never count as useful updates.
Every started proposal counts as one charged update even if it fails midway;
each replay proposal and FP64 audit update also counts once. Predicated slots
are recorded separately and their launch/wall cost remains charged.

The audit remains a host FP64 reference update from the saved pre-step state,
with original-unit comparisons and reference-endpoint adoption. Passing an audit
does not certify earlier updates. Every 200-update restart, weight and
original-model assessment boundary remains exact; a coincident audit runs before
the controller/assessment. CPU audits, transfers and endpoint adoption are fully
charged. They are intentionally present in matched controls as well.

Checkpoints bind the originating in-memory solve session, all device/host
numerical state, anchors, controller, generation and promotion state. Deadlines,
physical work and observations never roll back. Poll before each submitted
window and before/after audits; cap each submission at 32 updates. Cancellation,
deadline and device failure retain their status. Never replay a poisoned context
or turn a late certificate into a successful timing.

## Frozen controls and comparison

Freeze nine configurations before device work. All new configurations share the
same resident vector/update/launch structure, common conservative step,
32-update audit policy, 200-update controller/assessment and resource limits.

| Configuration | Purpose |
| --- | --- |
| Unchanged tuned FP64 | Practical fresh-solve baseline with its original step and assessment behavior. |
| Resident FP64 policy bridge | Tuned sparse operator, with the common conservative step, native product guards and 32-update audits. Measures the aggregate policy cost relative to unchanged tuned. |
| Resident matched FP64 | New compact segmented operator and metadata/guard path, all original FP64 coefficients and operands. Exposes operator/layout/reduction cost relative to the bridge. |
| FP16 uniform / selective | Matrix quantization compared directly with resident matched FP64. |
| E4M3 uniform / selective | Same comparison, including actual promotion/replay and guard costs. |
| E5M2 uniform / selective | Same comparison, without substituting another candidate on refusal. |

The bridge contrast changes several declared policies together and does not
isolate step versus audit costs individually. Bridge/matched operator trees may
differ, so that contrast includes reduction and trajectory differences. The six
quantized/matched contrasts use the same declared execution and reduction
structure, with precision-specific arithmetic and guards. Native recovery is
reported separately and is not an FP8 benefit. Historical GPUP-7 latency is
context only, never a new same-source paired timing.

Use the same four models (small-4, scheduling-20x5, irregular-2048,
irregular-32768), three timing repetitions, 10/10/10/30-second solve deadlines,
50000 total charged-update limit, solver seed 17, order seed 17001 and analysis
seed 17002. This is at most 108 fresh-process timings. Seeded order covers all
planned cells; skipped admissions retain their positions and are not replaced.
Retain host-only initial certificates as such, outside arithmetic speed claims.
Coverage retains all 108 planned timing cells in its denominator, with CPU
refusals distinct from attempted failures; filtering to admitted cells must not
inflate certified coverage.

Add nine separate irregular-32768 fixed-work profiles, one per configuration,
with 30-second deadlines and a target of exactly 2000 accepted logical updates.
This is an explicit diagnostic-protocol change: early certification is recorded
but does not truncate a profile. All audits, rejected/replayed work and guards
still count toward the 50000 charged-update ceiling and wall deadline. Each
200-update assessment remains; fresh final assessment is never borrowed from an
earlier success. Completion means the exact logical horizon, independently
verified endpoint and no interrupted/failure status. Report accepted and
physical throughput; partial horizons remain ineligible for paired profiles.
These diagnostic runs cannot replace fresh-solve timing results.
Forced continuation applies only to the research profile runner, including the
tuned control's profile; ordinary tuned solve termination is unchanged.

At most three additional 30-second microprofile jobs compare the fused guarded
product, the same product alone and the same guard alone on identical frozen
vectors/layouts. Each job covers resident matched FP64 and the six
candidates on CPU-validated inputs, with bounded fixed product counts. Product-only
jobs are explicitly unguarded diagnostics and have no solve/certification claim.
Record admission failures per vector; never classify an unadmitted guarded
product as accepted arithmetic throughput. Freeze synthetic admissible boundary
inputs and recorded trajectory inputs before running these diagnostics.
Counters separate packing/context, guard levels, sparse products, FP64 updates,
synchronization/transfers, audits, promotion/replay and host certification. Do
not sum overlapping fused-kernel intervals into a fictitious cost decomposition.

## Admission and stop rules

1. CPU first: freeze the format/guard/layout proof and run all eight existing
   GPUP-EXEC models for all six candidates plus resident matched FP64, at most
   400 charged updates per trajectory. Record initial certification but force
   diagnostic continuation for the admission horizon. Check the bridge/reference
   separately. Retain all scaling-256 and other numerical refusals. Record old coarse versus
   new detailed decisions, promoted fractions and bounds on identical vectors.
2. Mark useful-low eligibility only after a complete accepted 32-update audit
   window contains nonzero-input low products in both orientations without
   whole-operator promotion. Initial zero-dual work does not qualify. A format/
   policy/model failing this deterministic CPU criterion gets a retained
   accuracy/admission disposition; skip dependent quantized solve timings and
   profiles without replacement. Product diagnostics may still use valid frozen
   vectors and must not be described as a successful quantized trajectory.
3. Run native/device acceptance before the study. Include a fixed-work bridge/
   matched structural check on irregular-2048: no full-vector per-product
   transfers, no host per-product metadata scans, verified endpoint and declared
   counters. Failure stops dependent study work; do not spend time screening a
   known nonresident implementation. A slow but contract-correct resident path
   may proceed and retain its negative performance result.
4. If every nontrivial quantized cell lacks useful-low admission, stop those
   timings. Complete admitted FP64 controls and bounded operator diagnostics,
   report the numerical limitation and defer any accuracy-contract expansion.
   Do not introduce anchors/refinement, raise budgets, replace models or select
   a larger promotion cap to manufacture coverage.
5. Freeze exact source archive, executables, images, requests, model checksums,
   admission receipts and configuration order before execution. Preserve every
   failure/timeout and independently verify every available endpoint. No retry,
   automatic device substitution or successful endpoint scavenging is allowed.

## Proposed resource decision

Request a new task-specific allocation of **3600 GPU seconds from existing
unconsumed campaign authority**. Request **zero increase** to the cumulative or
phase ceilings. This is not reuse of GPUP-7's task allocation: its task is closed;
ADR-0041 must independently authorize GPUP-7R. Planning itself uses zero GPU time.

| Category | Proposed task cap | Maximum deadline-plus-overhead reservation | Existing phase headroom |
| --- | ---: | ---: | ---: |
| Screening timings | 2300 s | 2268 s: 9 configurations x 3 repetitions x (16 + 16 + 16 + 36) s | 2434.652522290 s |
| Ablation profiles | 450 s | 432 s: (9 fixed-work + 3 microprofile) x 36 s | 662.019812259 s |
| Repeatability acceptance | 850 s | 816 s: ordinary 180 + project 240 + four sanitizers x 90 + six jobs x 6 s | 2159.904162159 s |
| Total | 3600 s | 3516 s | 4088.675276095 s cumulative headroom |

The six-second allowance per job includes activity admission, worker overhead and
cleanup; all leased work is charged, including failures and missing telemetry.
Refuse before launch unless the task, category, campaign phase and cumulative
reservation all fit. The 84 seconds between planned reservations and the task cap
are overhead contingency, not a retry or extra-trial allowance. Skips release
allowance and never authorize another task.

Keep cumulative ceiling **25202.574545061 s**, independent campaign cap
**28800 s**, and baseline/screening/ablation/repeatability/finalist ceilings
**1800 / 11800 / 8100 / 5300 / 9000 s**. Current consumption is
**21113.899268966 s**; spending the entire allocation gives
**24713.899268966 s**, leaving **488.675276095 s** under the cumulative ceiling.
At full task caps the three affected phase totals would be
11665.347477710 / 7887.980187741 / 3990.095837841 s, each below its unchanged cap.

Preserve exactly the **17036-event** ledger prefix, SHA-256
**861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97**,
including the earlier 16816-event prefix and all protocols/artifacts. The new
resource protocol must chain to ADR-0040, record additional_gpu_seconds=0 and
allocated_gpu_seconds=3600, validate prior consumption and reject silent ceiling
changes. If another authorized task changes consumption first, recompute
admission without increasing these caps or assuming this proposal reserved funds.

Use only **GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48** under the shared host lease
and activity admission, without concurrent device jobs or automatic substitution.
Implementation CPU allowance is 21600 seconds, four build jobs, 8 GiB host RSS,
1 GiB aggregate device buffers, 2 GiB preparation memory and 32 GiB new artifacts.
Checked shape bounds remain 65536 rows/columns and 2^23 nonzeros. Check all live
buffers, snapshots, both sparse orientations, cached summaries and independent
verification lifetimes; refuse an oversized shape rather than weakening a bound.

## Acceptance and delivery

Before device work, independently validate all format boundaries and the actual
two-level directed bound program with integer/Fraction oracles. Include
cancellation, signed zero, subnormal/range extremes, prior scaling error,
transpose identity, mixed FP32/FP64 operands, tight-pass/coarse-fail examples,
native budget exhaustion, memory limits and stale operator/generation rejection.

Test failures at both product orientations and every position in a window;
complete restoration, deterministic promotion caps, predication/counter charging,
reference adoption and 200-update boundaries. Cover cancellation/deadlines before
and during audit/recovery, device failure, cross-session checkpoints, corrupted
evidence, oversized counters, signed-zero replay and interrupted profile readers.
Use synthetic fault injection and exact counterexamples; do not infer these
contracts from successful solves alone.

Run full pinned-native bash tools/check.sh with no GPU work, all existing ordinary
device tests, new product/guard/controller differentials, six candidate acceptance
cases on small-4/irregular-256/scheduling, fixed-work same-device bitwise replay
and all four scoped sanitizers. In the project acceptance reservation, cover all
18 candidate/model cells plus the FP64 controls and resident structural check.
Ordinary builds remain toolkit-free and runtime/unsafe ownership stays unchanged.

Produce a separate GPUP-7R report and strict versioned solve/verify/replay evidence.
Report certified coverage and full fresh-solve cost including packing, metadata,
guards, transfers, audits, recovery and final certification. Separate raw and
accepted nonzero-input low coefficient-products, native work, promoted fraction,
replayed work and initial host-only certificates. Report paired ratios/uncertainty
only for eligible verified cells, with no hardware-throughput extrapolation from
three repetitions. A recovery-only solve is not a quantized speedup.

Acceptance means verified numerical/resource contracts and a reproducible bounded
comparison, not a required speedup. Update limitations and task state, retain all
old evidence and commit locally after acceptance. Publication and merge remain
outside this proposal. GPUP-8's conditional hardware disposition follows this
resident/admission investigation; it gains no automatic allowance or mandate.
