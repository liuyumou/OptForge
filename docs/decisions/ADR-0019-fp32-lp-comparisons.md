# ADR-0019: Explicit FP32 LP Comparisons and External COPT Controls

Status: accepted by the maintainer on 2026-09-16 before implementation.
Scope: GPUP-5 only; amends ADR-0012's reserved selector and SPEC-0012/0013.

## Decision

Extend cuda-lp-tuned with an explicit lp-precision-v1 document. Absence preserves
all prior behavior and wire emission. cuda-lp-quantized remains unavailable.
Precision execution requires resident/necessary/warp32_v1/separate execution.
Matrix/products/accumulation/state are respectively 64/64/64/64, 32/64/64/64,
32/32/64/64, 32/32/32/64 or 32/32/32/32. Product operands match product width;
updates, control, objective and bounds remain FP64. Working-state FP32 requires
fixed FP64 correction. Every setting, including no correction, is explicit.
Rounding is nearest-even, contraction disabled, subnormals retained. A single
canonical converted scaled matrix supplies both orientations. Guard nonfinite
intermediates, overflow and nonzero-to-zero conversion/product loss before
projection. Numerical guards stop without precision replay or backend fallback.

Use an outward upper bound on both original and represented operator norms and
a downward-rounded step no larger than the legacy step or 0.9 / that bound.
The new precision FP64 control uses the same conservative step policy. Existing
controls are unchanged. Fixed corrections recompute the scheduled final update
in original-operator FP64 from its saved pre-step state; adopt the result without
an audit threshold. Record discrepancies. Re-round working state for continuation,
keeping the corrected endpoint for host assessment. Both physical updates consume
work/time. No audit acceptance, rollback, promotion or demotion is introduced;
SPEC-0012 requirements 24-29 remain GPUP-6, not implicit GPUP-5 behavior.

Precision records/endpoints and campaign/trial documents use version 4; precision
settings use version 1. Earlier strict formats remain unchanged. Mixed capability
metadata is explicitly versioned. Precision kernels have a separate code object.
Host validation and outward certification on the immutable original model retain
all mathematical authority. Existing availability fallback is pinned HiGHS.

COPT 8.0.6 is external Python study tooling, not a runtime adapter or unsafe
boundary. Use isolated bundled bindings, PDLP CPU and one-device GPU, explicit
parameters, and original-model primal/dual witness assessment by Rust. Record
actual CPU/GPU execution, native identity and all unavailable/failed outcomes.
Never infer certified success or GPU execution from requested settings.

## Frozen study and resources

Twelve configurations: archived matched; existing tuned resident/necessary/warp32/
separate; four FP64-master precision modes without correction; FP32 products and
accumulation with FP64-master correction every 32 iterations; the same with FP32
working state; host-lp; pinned HiGHS; COPT CPU PDLP; COPT GPU PDLP. Twelve existing
development instances, three randomized timing repeats and one profile on the
existing four profile instances total 480 attempts. Preserve input hashes, splits,
seeds, stopping tolerances and existing limits. No validation/held-out solve or
supported preset. Record all costs, failures, incomplete coverage and uncertainty.

Carry forward the entire 1902-event canonical prefix (SHA-256
35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543) and
902574545061 charged nanoseconds. New screening allowance is 3600000000000 ns;
cumulative ceiling 4502574545061 ns; campaign cap 28800 seconds and phase caps
remain. Preserve original authority/output binding and archives. Acceptance gets
900 separate leased GPU seconds. CPU validation ceiling four hours, four jobs.
Every GPU job, including COPT preflight, holds the shared host lease, sequentially
with CPU acceptance. Unfinished evidence at a cap is interim, never full acceptance.

## Acceptance

Full pinned-native tools/check.sh; independent rational/rounding and operator
checks; complete continuation/correction/work/guard tests; strict schema, legacy
replay, code identity and fallback tests; COPT original-model and dual-sign tests;
regular device acceptance and all four scoped sanitizers; frozen study and report.
No toolkit/device is required by ordinary Cargo builds. Existing unsafe boundaries
and GPUP-1 authority regressions remain. GPUP-6 is next only after required gates.

## External-control availability

Local 8.0.6 API inspection confirms no public PDLP iteration-limit or random-seed
parameter. COPT controls retain the hard ten-second supervisor limit and explicit
accuracy targets; iteration counts are observed, not claimed to be identically
bounded. A reported count above 50000 is classified work_limit even if its native
status is optimal. Record this limitation in every witness and the report.
