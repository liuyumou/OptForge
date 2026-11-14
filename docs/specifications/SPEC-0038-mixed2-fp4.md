# SPEC-0038: FP4 tensor increments, FP64 state, and larger-scale evaluation

The user authorizes implementing the recommended tensor-core approach, careful
measurement and diagnosis, sustained optimization, and larger benchmarks.
[ADR-0071](../decisions/ADR-0071-mixed2-fp4.md) records the decision. This new
independent task supersedes the completed pilot's no-follow-on restriction for
this scope only. Historical numerical sources, evidence, decisions and closed
allocations remain exact. Commit locally only; no public default or GPUP-9 release.

## Numerical contract

Use a separate research executable and new source-bound SM120a image. Original
FP64 matrices, FP64 state, power-of-two row scaling, projected updates and an
independent original-model CPU checker retain authority at both 1e-7 and 1e-9.
FP4 E2M1 component products approximate increments from original-A FP64 references
refreshed at most every 32 updates. Two/four components are explicit lanes; no
runtime timing selection. Component MMA uses FP32 accumulation, followed initially by FP64
rescaling/reconstruction and state updates. Versioned development may replace
only temporary reconstruction with FP32 under the explicit bound below; state,
reference products, addition to the reference and updates remain FP64. Exclude E2M1 subnormal code 1 (and 9)
from the new codec to avoid unspecified PTX subnormal handling. Scales are bounded
in [-48,48]. Unscaled 32-term component dots are quarter-integer sums bounded by
1152 and exactly representable in FP32, independent of summation order, under the
admitted tensor instruction arithmetic. Verify this assumption on the new image
against exact integer products, including every admitted code pair.

Precompute outward row/column sums of original magnitudes, representation errors
and component magnitudes. Combine these with per-vector-block maxima of increment,
quantization error, component magnitude and reference magnitude, using outward
FP64 operations. Include reference, subtraction, reconstruction and addition
rounding. These are local original-product enclosures, not a global trajectory
proof. Do not substitute heuristic noise estimates for these bounds. Bound each
projected update's local product contribution by its step-scaled enclosure.
Original-model progress checks require both primal and dual residual aggregates
to improve by 1% (with the final tolerance as floor), or a valid final certificate.
Guard, conversion, nonfinite or progress failure restores an exact checkpoint;
strictly promote x2 to x4 to permanent native, retaining physical work outside
rollback. Cancellation/deadlines precede certification at completed boundaries.
Bitwise checkpoint restoration includes signed zeros, logical state and generation.

## Development and evaluation

CPU arithmetic/guard contracts and full native acceptance precede new device
admission. GPU admission includes exact integer component tests, independent
rational enclosure checks, native schedule comparisons, solver/lifecycle/recovery,
original certificates, and all four scoped Compute Sanitizer tools. Never silently
retry failed development: preserve each source version and full failed reservation.
Development timing is exploratory and versioned; freeze a new confirmation only
after correctness and image-specific sanitizer admission. No scientific retry.

Retain the twelve historical small/medium families as scope controls, and add
dense generic 1024 and 2048 full solves (4x and 16x dense512 coefficients).
Before any timing on them, add dense-coupled-1024 and dense-coupled-2048: the
same generic dense coefficients plus 0.5 on the cyclic next column. Their known
nonzero primal/dual construction is used only to form the model, never to initialize
the solver. These cases test stronger coupling and longer trajectories. The
coefficient, dimensions and cap are fixed prospectively; retain unfavorable results.
The bounded window pilot compares 8/16/32 on both controls over two blocks.
Additional larger product or solver cases require memory admission within the
same ceiling and a prospectively recorded roster; refusal remains visible.
Measure strong native and FP4 with identical FP64 state, scheduling, transport,
audit limits and final tiers. Retain full work counts, accepted windows, recovery,
conversion, representation preparation, device allocation, setup/destruction,
independent checking and durable delivery. Prepared steady-state solves and
cold/amortized costs remain separate. Uninstrumented complete delivery is primary;
coarse phase/event diagnostics must quantify perturbation. No per-kernel host
instrumentation in the measured default path.

Use early development evidence to select the best deterministic candidate and
explain the choice before freezing. Confirmation uses fresh balanced paired
sessions, fixed initial states, independently randomized blocks, and no cell
omission. Define final roster, block count, seed and candidate in a source-bound
freeze manifest before execution. Aim for 32 blocks for primary larger dense
comparisons when budget and measured variability permit; report exact median
order-statistic intervals and shared-device/constructed-workload limitations.
This is a research performance evaluation, not production adoption. Report
absolute latency saved, setup break-even request count and sensitivity to sample
size; 1.10x remains a provisional adoption value, not a diagnostic veto. Preserve
negative and inconclusive findings and every development cost in the report.

The new executor and independent service admit model files up to 384 MiB; the
2048 fixture is approximately 225 MiB. CPU-only large-checker admission precedes
CUDA. Initial unsupported FP4 preparation promotes directly to native and records
the refusal. Diagnostic unguarded product batches are explicit read-only ablations
and never enter a solver or acquire certificate authority.

Development v1 found FP64 reconstruction unfavorable at every measured size.
Development v2 uses FP32 power-of-two rescaling and summation of the exact MMA
component dots. For b padded blocks and K components, every FP32 intermediate
is bounded by 1152*b*K*K*2^96 (<2^128 for b<=64,K<=4), and every nonzero
summand is a multiple of 2^-98, avoiding subnormal accumulation. At most
b*K*K+b+8 rounded additions lie in the reconstruction; the upward coefficient
(4*b*K*K+32)*2^-23 safely exceeds its standard gamma bound. Multiply by the
cached component row L1 and vector component magnitude maximum. Retain the
original FP64 reference/subtraction/addition bounds and independent rational
checks. This prospective variant does not reinterpret the retained v1 results.

Development v3 proposes vector components using FP32 arithmetic, then bounds
the actual decoded components against the FP64 increment. Metadata maxima use
upward FP64-to-FP32 conversion and integer warp maxima. A warp cooperatively
gathers the block summaries; conversion back to FP32 is exact because each
stored summary came from FP32. These summaries remain outward
bounds when stored back as FP64. Normal-component and scale limits are unchanged.
An explicit window_max of 8, 16 or 32 applies equally to both lanes. The frozen
study must state its choice before execution. State and reference arithmetic
remain FP64; exact power-of-two multiplication replaces general ldexp where its
exponent is bounded, with native bitwise differential admission.

Both controls receive exact CPU improvements: independent original rows/columns
are evaluated on four workers while each row/column keeps its serial order;
certificate sums retain the original tree and use magnitude-ordered FastTwoSum
only for at most 2048 bounded leaves (nonzero fields in [2^-100,2^100]). A path
has at most eleven live additions: no intermediate can overflow or underflow.
Original arithmetic remains the fallback over the rest of binary64. Full-field
bit comparisons against the original checker, including extreme values, signed
zeros, padding and refusals, precede new device admission. The original serial
checker remains independently available and unchanged.

The checker also uses the already admitted exact SHA-256 implementation for
model/endpoint identity, with long-model hashes compared to independent hashlib.
This optimization is shared by both controls and changes no mathematical field.

One development racecheck run with default all-process injection exited 11 with
zero reported hazards. Eight prospectively ordered fresh processes (four on each
old/new image) did not reproduce it. The cause remains unassigned. Preserve that
failure and its full reservation. Subsequent sanitizer admission explicitly uses
application-only injection: all CUDA work is in the root executor; the independent
checker already has CUDA_VISIBLE_DEVICES empty and receives separate CPU admission.
This is a process-scope correction, not evidence that the exit's cause is fixed.
Require a fresh full four-tool pass; retain this limitation in the final report
and do not infer production reliability or release a public preset.

## Independent resource envelope

160000 CPU seconds: implementation 40000 (512 preparation), native 12000,
acceptance 30000, development 30000, confirmation 32000, reporting 12000,
cleanup 4000 (128 closing). GPU 24000 seconds: acceptance 6000, development 6000,
confirmation 12000; CPU caps also constrain GPU wall time. Four CPU slots,
16 GiB sampled RSS, at most 12 GiB owned device buffers, one pinned shared SM120
lease, unchanged tools/lp_cpu_admission.py supervisor. Receipts and immutable
failed sources: artifacts/gpup-mixed2-fp4-v1. Never transfer historical funds.
Close only after final acceptance, preservation, portable replay and empty cleanup.

Development v4 moves the immutable initial-state observation into session setup,
shared by both controls; repeated solves clone its exact fields. It also admits
an explicit fixed_audit request (default false) that retains audit_max=200
instead of shortening the interval to 32 near convergence. Both controls use the
same schedule in each comparison. Local guards, per-window original references,
progress requirements, exact rollback and final certificate authority are unchanged.
Measure the extra updates against reduced independent assessment cost before
selecting the confirmation configuration. Preserve adaptive-schedule results.

Confirmation selection: native uses its cheaper 32-update submission window;
FP4 x2 uses 16-update original-reference windows, avoiding the extra convergence
assessment observed with x2/32. Both use fixed maximum-200 audits. Freeze 32 blocks,
16 families, both final tiers and three solves per tier per fresh session. Balance
native-first/FP4-first exactly 16/16 per family; randomize family order independently.
The 32 blocks are session-level replications, not 96 independent samples. Report
exact median intervals simultaneous over 32 family/tier ratios and 32 absolute
savings, plus first-16 sensitivity and order splits. The pilot suggests millisecond
value on larger dense solves; it does not justify production adoption or universal
workload claims. Preserve all small-family regressions and refusals.

A separate predeclared four-block timer ablation removes only phase-clock reads
and run-window CUDA event records/elapsed reads, retaining synchronization, limits,
original arithmetic and the same admitted image. Compare native and FP4 across
128/512/1024/2048 generic and 2048 coupled families, three strict solves per session.
Require complete numerical transcripts to match, excluding timer and checker-binary
identity fields. This quantifies measurement disturbance without changing the
frozen confirmation executable or extrapolating per-kernel timing.
