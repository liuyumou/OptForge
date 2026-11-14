# SPEC-0036: MIXED2 CPU numerical and complete-cost admission

Status: implemented CPU admission contract, 2026-11-12; device execution conditional.
The user requests GPUP-MIXED2 from the [roadmap](../plans/gpu-lp-precision-roadmap.md).
[ADR-0069](../decisions/ADR-0069-mixed2.md) fixes this bounded implementation.

## Numerical contract

An isolated, safe Rust CPU reference stores canonical CSR coefficients in FP32
and widens them exactly for sequential FP64 fused multiply-add. Iterates, products,
accumulators, checkpoints and control scalars stay FP64. The transpose uses the
same stored coefficients, without independent quantization. Initial scaling is
identity: no hidden equilibration or replacement of original data. Original FP64
coefficients remain mandatory for residuals and independent final 1e-9 checking.
Invalid CSR, nonfinite inputs, FP32 overflow or nonzero-to-zero conversion refuse.
FP32 subnormals are supported by this CPU reference; device FTZ must be separately
admitted. Refuse any nonfinite product or enclosure rather than report success.

For each output compute an outward FP64 bound on sum(abs(A-A32)*abs(x)) plus
sequential FMA rounding. Every positive bound operation rounds upward; each FMA
contributes upward u/(1-u)*abs(result) plus one binary64 minimum subnormal, with
u=2^-53. This bounds the error against the exact original dot product, not the
trajectory or an optimality certificate. Validate independently with rational
arithmetic, cancellation, extreme exponents, subnormals and transpose cases.

A reference window transaction owns an entire caller checkpoint (opaque bytes),
accepts only finite original-model primal AND dual residual progress, a finite
nonnegative declared local error allowance, and positive attempted work. Error
budget breach or either residual's failure to fall by at least 1% rolls back all
checkpoint bytes and promotes permanently to native. Cancellation restores bytes
without publishing a candidate. Physical attempted work remains charged even on
rollback; logical work advances only on acceptance. Overflow of counters refuses
before mutation. This 1% policy is operational, not a convergence guarantee.
A real executor must serialize all iterates, averages, counters and control state;
this CPU transaction alone does not prove executor checkpoint completeness.

No public solver registration, CUDA implementation, lower-precision state or new
certified solve is included in this CPU admission. A later device slice needs
useful nonzero accepted mixed windows, native recovery, bounded cancellation,
original-A audits and independent original 1e-9 certificates. Zero-work or
zero-useful-window outcomes cannot qualify. Prior REFINE and resident quantization
failures motivate this explicit requirement; the RESIDENT2 executor is not a base.

## Frozen cost admission before analysis

Use all 32 blocks and twelve families of nativefast/certified-1e-9 candidate
records: DELIVERY4 cold (hash acceleration, overlap) and DELIVERY3 prepared
(batching), separately. No timing-selected family removal. Eleven bounded
families must retain certification; intentional infinite-bound refusal remains
visible. Prepared estimates use medians of three per-solve deliveries in each
session and report setup/teardown separately, never as cold cost. Bind retained
archives and source versions; do not rerun historical scientific cells.

The prospective target is 1.10x median block geometric ratio across dense128,
dense256 and dense512, with each bounded-family median extra cost at most
max(2% of control, 0.10 ms), unchanged coverage, positive useful mixed work and
fresh original certificates. Cold and prepared qualify separately. Two benefits
and 22 family guards use simultaneous two-sided 95% binomial median intervals
(Bonferroni 24 metrics, 32 blocks). Retained-data forecasts are descriptive:
these intervals describe assumed transformed costs, not a new measured effect.

For every individual solve use T_new = T-A+w*A/s+O before session reduction.
All GPU event time is only an upper bound on A: matrix-only attribution is absent.
Report fractions 0.25, 0.5 and 1; speeds 1.25, 1.5, 2 and 4; work 1, 1.25 and 2;
added costs 0, 0.10, 0.50 and 1.00 ms, plus ideal removal. Freeze these scenarios
before analysis. Include representation, transfer, guard, correction, fallback
and checking in O; report their separate nonnegative allowance and unknown status.
Even the ideal bound failing defers a route. A promising whole-event bound with
unknown matrix fraction admits no solver study: require a separately funded
attribution pilot and measured overhead/work first. No new device allocation.

## Resources, acceptance and delivery

Independent ceiling 16000 CPU seconds, zero GPU. Phases: implementation 4096
(including 512 conservative preparation), native 8000, diagnosis 2048, reporting
1200, cleanup 656 (including 128 closing administration). Four CPU slots, 16 GiB
sampled RSS, unchanged in-container supervisor. Receipts and immutable development
versions: artifacts/gpup-mixed2-v1. Failed reservations remain fully charged;
closed historical allocations transfer nothing. No scientific retries.

Acceptance: Rust format/clippy/tests, independent rational differential tests,
cost reducer malformed/coverage/boundary tests, portable retained-data replay,
full tools/check.sh with native HiGHS, source/history checks and empty supervisor
cleanup. Preserve all old evidence and handoffs; update only current navigation.
Write positive, negative and inconclusive findings and limitations to the
[report](../benchmarks/lp-mixed2.md) and handoff. Commit locally only.
CPU admission can close with device deferral; this does not claim an implemented
GPU solver, a retained speedup, GPUP-8 completion or GPUP-9 release.
