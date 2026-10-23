# ADR-0042: Bounded hybrid Tensor Core component execution

Status: accepted, 2026-10-23, by explicit user approval of the implementation plan
Owner: numerical backend and experiment tooling
Introduced: GPUP-8
Superseded by: none

## Decision

Implement isolated research-only lp-tensor-v1. Canonical 32x32 tiles with at least
512 nonzeros use the same signed block-scaled 56-bit represented operands in
both orientations. Other coefficients remain native FP64. The block exponent is
one above the maximum unbiased binary exponent; extract magnitude bits toward
zero, record an outward residual, and refuse nonfinite/range/lost-nonzero inputs.
INT8 and FP16 use eight signed 7-bit digits; BF16 uses fourteen signed 4-bit
digits. INT8 mma.sync m16n8k32 accumulates INT32;
FP16/BF16 m16n8k16 accumulates FP32. Every partial sum is exact: absolute bounds
are 32*127^2=516128 and 32*15^2=7200. BF16 digit products are exactly representable.
Reconstruct tile dots in signed 128-bit integers (117 magnitude bits suffice),
then round once to FP64; deterministic outer reduction includes the native
remainder. Independent components of the current vector occupy MMA columns.
A represented-operand SIMT control uses the same exact tile dot and rounding.

Preserve FP64 resident state, 1e-7 original-unit product/audit budgets, conservative
norm/step, 32-update audits, 200-update numerical boundaries, complete rollback,
charged replay, uniform sticky native promotion and fresh original-model 1e-9
host certification. Bounds include coefficient scaling, both operand residuals,
reconstruction and remainder rounding. Prepared operators are immutable and
session/generation-bound; validate physical counters before aggregation.

This accepts only the bounded additions to SPEC-0012 requirements 16-28 and
SPEC-0021 guarded-product/window requirements. No historical numerical contract,
source/image/evidence is changed. Ordinary builds remain toolkit-free; existing
driver safety boundaries apply. No cuBLAS dependency, FP8 Tensor variant,
refinement/assessment combination, sessions or preset is admitted.

## Study and resource authority

Freeze six configurations: INT8/FP16/BF16 Tensor, represented SIMT, policy-matched
FP64 and unchanged tuned FP64. All eight inherited models undergo CPU admission;
eligible trajectories run 400 logical updates. Dense-block-1024 and
 dense-block-65536 each have five fresh-process repetitions/configuration (60
cells), deadlines 10/30 s, 50000 charged updates, inherited seeds and tolerances.
Twelve separate profiles force 2000 logical updates; three product diagnostic
jobs use 30 s each. Refused/interrupted cells remain without replacement/retry.
Freeze source/executable/image/requests/order before study execution.

Allocate 3000 GPU seconds from existing headroom: screening 1600, ablations 550,
repeatability 850. Reservations including six-second job overhead total
1560+540+816=2916 seconds. Keep cumulative ceiling 25202.574545061 seconds,
independent campaign 28800 and existing phase ceilings. Starting consumption
21359.585855789 seconds; full allocation leaves 842.988689272 seconds.
Bind to the exact 17132-event prefix SHA-256
930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035.
Use GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 only under shared admission.
CPU cap 21600 seconds/four jobs, RSS 8 GiB, preparation 2 GiB, device 1 GiB,
artifacts 32 GiB. Additional GPU seconds and future reservations are zero.

## Acceptance and completion

Independent integer/Fraction proofs precede CPU admission and device work.
Verify actual MMA instructions, at most 128 registers and zero spills; ordinary
and new device/controller/replay suites and all four scoped sanitizers pass.
Run full pinned-native tools/check.sh including CPU/docs/smoke, strict schema and
source-only portability tests; independently verify every available endpoint.

Completion requires useful admitted INT8 and at least one FP16/BF16 certified
nontrivial solve, and one fresh-process total-latency gain over unchanged tuned
FP64. All five repetitions of a comparison certify, candidate coverage cannot
fall below control coverage over both timing models, and paired bootstrap
speedup intervals exclude one after Bonferroni adjustment across six candidate/
model comparisons (family confidence 95%, 10000 resamples, seed 17002).
Retain all comparisons; microbenchmarks/incomplete profiles do not qualify.
If any completion requirement fails within allocation, preserve the result and
leave GPUP-8 incomplete. Do not advance GPUP-9 or enlarge scope/budgets.
Local commit follows applicable checks; publication/merge are not authorized.
