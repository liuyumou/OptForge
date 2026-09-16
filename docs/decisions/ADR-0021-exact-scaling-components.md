# ADR-0021: Exact Scaling and Component Sparse Products

Status: accepted by the maintainer's explicit implementation request, 2026-09-16.
Scope: GPUP-5B, a bounded research slice before GPUP-6.

## Decision

Preserve existing runtime settings, records, replay trajectories, code objects,
reports and archived evidence. New arithmetic exists only behind the
precision-research Cargo feature and in a standalone research executable with
strict research-v1 requests/evidence and a separate provisioned CUDA code object.
Ordinary builds require neither toolkit nor device. Unsafe/host-authority
boundaries remain unchanged. No recovery, correction, fallback or preset is added
to this research executor; unavailable execution is an unsuccessful observation.

Use the existing resumable FP64 controller and original-model certification.
Accept explicit positive finite diagonals through a feature-gated host constructor.
Compare default scaling with nearest-power-of-two diagonals in logarithmic distance,
computed by integer significand comparison rather than platform logarithms.
Reject inexact/range-losing power-of-two transformations of finite model data.
Compare FP64 and exactly representable FP32 storage. Separately compare factored
Dr A Dc products using the original FP64/exact-FP32 coefficients and FP64 scales.
Both orientations derive from one canonical representation. Restrict the step
using conservative bounds on original and represented operators; paired scaling
controls share the same bound and downward-rounded step policy.

Represent each finite FP64 operand by a normalized mantissa split into three FP32
components and an integer exponent. Three components preserve every input bit;
two deliberately discard the third and record the residual. Compare reconstructed
FP64 multiplication with all four/nine FP32 cross-products. Each cross-product
uses an explicit FP32 multiply and FMA residual, followed by fixed FP64 compensated
recombination, exponent restoration and warp32-v1 FP64 reduction. Implicit
contraction is disabled; gradual underflow and nearest-even remain. Master state,
updates, bounds, objective and controller stay FP64. Check intermediate range
failures before projection; never confuse exact inputs with exact/replay-identical
arithmetic. Charge splitting, exponent handling, buffers, guards and transfers.

## Frozen experiment and resources

Twelve configurations: existing tuned-FP64, precision-FP64, storage-FP32; research
default-FP64; power2-FP64/FP32; factored-FP64/FP32; components2 and components3,
each with reconstructed-FP64 and FP32 cross-products. Keep the twelve development
models, seeds 17/17001/17002, 1e-9 tolerances, controller/resource settings and
randomized blocking. No validation/held-out data. Freeze before GPU measurements:
432 full timings, 48 profiles on the four existing profile models, 336 equal-work
200-proposal runs (seven blocks), and 24 Systems traces on small-4/irregular-2048.
No scheduled correction or adaptive recovery. Failed/incomplete runs remain.

All GPU work, including acceptance and failed attempts, uses the shared lease and
the original screening ledger. Preserve the 3288-event prefix SHA-256
b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef and
1467266874696 charged nanoseconds. Cap new study work at 900 seconds and acceptance
at 300 seconds, with a combined 1200-second cap inside the existing
4502574545061-nanosecond ceiling and unchanged campaign/phase caps. Admit complete
deadline/cleanup reservations before work. Exhaustion stops with explicit missing
evidence, never another allowance. Four build jobs; four-hour CPU validation ceiling.

## Documentation and acceptance

Before GPU measurements, preserve the previous diagnosis in a new rounding note
with reproducible exact-rational analysis, identities, formulas and sampled CPU
results. Record all deferred directions in a candidate register with prerequisites.
Do not rewrite the earlier report or its evidence. Keep observations, arguments,
hypotheses and candidates distinct.

Require strict evidence/provenance checks, independently certified original-model
witnesses, exact-rational rounding/range/scaling tests, CPU/device arithmetic and
controller-boundary differentials, cancellation/memory/work/fault tests, historical
compatibility, full pinned-native tools/check.sh and all four scoped sanitizers
sequentially. Report coverage, paired single-solve latency, convergence, representation,
arithmetic, packing, memory and transfers; a negative speed result is valid evidence.
