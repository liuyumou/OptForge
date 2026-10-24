# ADR-0046: Expanded working state inside audited windows

Status: accepted by explicit user implementation request, 2026-10-24.
Scope: one bounded GPUP-8 continuation, `lp-tensor-expanded-v1` and
`gpup-tensor-expanded-v1`. Historical ADRs and evidence remain exact.

## Decision and numerical contract

Working primal, dual and extrapolated vectors use Expansion64 within each
at-most-32-update window. Externally committed state, restart control and
checkpoints remain FP64. Before the last update, canonicalize both vectors to
FP64 round-to-nearest/ties-to-even, preserve that exact penultimate state in the
host metadata and device reference buffers, and re-encode it exactly for the
expanded candidate step. Convert the candidate endpoint for the existing audit.
Run the retained warp32 FP64 reference update from the same penultimate input;
on success adopt its endpoint and invalidate expanded working buffers.

Length one uses the unchanged starting FP64 point as penultimate input. Zero
length refuses. Windows clip at the existing 200-update controller/assessment
boundaries. Both vectors validate before publication. Failure, interruption or
cancellation restores the whole window checkpoint. Physical work, reference
work and replay are charged and never rolled back. Recoverable expanded range
or budget failures request uniform sticky native promotion and whole-window
replay through retained FP64 kernels. Unrecoverable/device failures stop.

Expansion64 has 64 significant bits, normal exponents -1022 through 1023,
minimum unit 2^-1085, signed zero and nearest-even rounding. Store three FP32
24/24/16-bit component arrays plus packed exponent/sign metadata (16 bytes per
coordinate, excluding separately accounted scratch). Normalize every declared
scalar primitive. Proved FP32 error-free-transform fast arithmetic and the
compact integer full-range construction must produce identical results.
Prohibit incidental reassociation/contraction. Legacy trajectory byte equality
is replaced only for this candidate; exact new-candidate replay remains required.

Retain the 56-bit matrix and use 64-bit vector main parts with separate magnitude
and sign. INT8/FP16 use 8 by 10 components (80 pairs), BF16 14 by 16 (224 pairs).
The padded tile has 32/64/112 MMA instructions respectively per product. The
32-term main dot magnitude is below 2^125 in signed 128-bit accumulation. Retain
all residuals, sparse terms and coefficient-error bounds; reconstruct into
Expansion64. Expanded dual projection uses positive-step
`raw - clamp(raw, step*lower, step*upper)`, with explicitly rounded finite bounds
and symbolic infinities. Prove its enclosure before admission.

Packing, arithmetic and conversion errors receive conservative original-unit
enclosures inside the existing 1e-7 budgets, with no extra allowance. Nonfinite
values, overflow, nonzero-to-zero boundary conversion and unproved ranges refuse.
Every required host assessment and delivery certificate remains fresh and uses
the actual returned FP64 endpoint at the unchanged 1e-9 tolerance.

## Implementation and evidence boundaries

Add separate CPU, CUDA and solve/trace-cpu/verify/replay research interfaces.
Load reference and native-fallback kernels from the retained hash-bound image;
expanded kernels have a separate image. New versioned counters must validate
the wider digit layout without weakening historical validators.

Bounded serial preparation tables, predecoded Gram inputs, per-solve assessment
indices/scratch and nonduplicating serialization may remove host overhead while
preserving numerical/reduction order and full fresh-solve charging. The matched
FP64 control shares those host changes; SIMT shares expanded arithmetic; tuned
FP64 keeps its retained executable/image. No shared cross-solve cache or solver
thread increase. Profile instrumentation distinguishes host scopes and CUDA
events; instrumentation overhead is charged. Timing boundaries stay unchanged.

Retain all old source/image/request/report/journal bytes. Reuse passed unchanged
checks through complete source/input/binary bindings, never by merely carrying a
pass label. New candidate dependencies require new acceptance. No historical
passed check, numerical endpoint verification or profile is rerun. The complete
accepted gate/resource plan is [the expanded-window continuation](../plans/lp-tensor-expanded-windows.md).

## Resource amendment

Add 24000 CPU seconds; cumulative ceiling 77640. Combine with 7600 unused seconds
for 31600 prospective seconds, starting at 45902.541829170; maximum
77502.541829170. Preserve 137.458170830 unassigned seconds. Individual allocations
and prior-accounting bindings are recorded in
[the authorization](../benchmarks/data/tensor-expanded/authorization-v1.json).

Allocate 1760 existing GPUP-8 GPU seconds: acceptance 450, profiles 320, timings
990. Explicitly release obsolete unused warp32 reservations, retaining charges
and original cap records. GPUP-8 phase ceilings become repeatability 1070,
ablations 520, screening 1410; their sum stays 3000. Maximum task/campaign use is
2992.909411024 / 3000 and 24352.495266813 / 25202.574545061. Every campaign phase
ceiling and independent 28800 ceiling is unchanged. Retain the exact 17412-event
ledger prefix SHA-256 `9913d391634bdb0f74012be909be377e5a693d00b76e6882abcf336796ac863e`.

Use the unchanged cooperative supervisor, four-times-wall charges and memory
policy. No bootstrap rerun, host access, container change or supervisor change.
A formal stage failure retains its full reservation, stops science and leaves
later allocations unused. No automatic retry or transfer. Delivery may use its
separately reserved reporting funds after preserving the closed failure journal.

## Completion and future work

All 76 cells, horizons, deadlines, ordering, useful integer/floating requirements,
five certified repetitions, coverage and six-comparison multiplicity adjustment
remain unchanged. Profile gain and resource admission precede timings; 1.25
resource multiplier and 120-second tail stay fixed. All new endpoints verify
independently once, including available failure/interruption endpoints. A failed
gate yields an incomplete report. Commit only after applicable acceptance;
publication, merge and GPUP-9 are outside scope.

Expanded state across audits requires a separate observation-only audit contract,
cross-window error/recovery proof, complete expansion checkpoints, CPU adversarial
validation and its own resource/study proposal. It has zero allocation here; see
[the future-work section](../plans/lp-tensor-expanded-windows.md#future-work).
