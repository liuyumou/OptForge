# SPEC-0031: Corrected FP4 state and resident solve acceleration

Status: implemented; both frozen comparisons complete, no broad latency retention
Delivery: [measured report](../benchmarks/lp-fp4-accel.md)
Date: 2026-11-11
Decision: [ADR-0063](../decisions/ADR-0063-fp4-corrected-acceleration.md)

The user requests fixing the diagnosed overhead/recovery problems and sustained
performance improvement. This is a new implementation and allocation. All
SPEC-0030 sources, results, policies and charges remain exact and closed.

## Numerical contract

Implement a separate bounded research executor for coupled models up to 512 rows
and columns. Preserve original-model independent 1e-7/1e-9 feasibility, conservative
bound and gap authority. Keep the supported public native solver unchanged.

The corrected lane uses E2M1 tensor products and retains local FP32-pair state
corrections instead of discarding every encoding remainder. For original operator
A=A0+E and vector v=v0+r, compute A0*v0 with actual FP4 MMA and add A*r+E*v0 using
compensated FP32 arithmetic. Both orientations share original coefficients and
packed representation. Account for both correction products; no nonzero term is
silently dropped. This is mixed arithmetic with FP4 tensor products, not FP4-only
arithmetic or a proved global trajectory enclosure. No ordinary iteration makes
a host/FP64 state round trip. Preserve correction state in checkpoints/conversion.
The scalar-corrected development path passes numerical admission but its per-update
correction dot products are slow. Retain it as an explicit scalar control.

The faster candidate recenters each at-most-32-update window: compute original-A
and transpose products of the window's resident state in FP64 once, then apply
FP4 products to the changing increments about those anchors. Persistent FP32-pair
state retains the updates. This includes an explicitly charged device FP64
reference calculation per window, not an FP64 calculation per ordinary update
or a host state round trip. Matrix approximation times increment and incremental
encoding loss enter the operational local guard. Packed checkpoint views are
canonicalized at window completion; temporary window anchors are recomputed on
restart from complete persistent state. A separate CPU component recurrence
checks this changed algorithm before new device/full-trajectory admission.

An explicit tile-parallel variant uses separate stream-ordered x, y and guard
launches, with eight warps per output tile and deterministic ascending-warp
reduction. The native control receives the same parallel reduction. No inter-CTA
spin barrier or atomic floating accumulation is used. Pending flags become sticky
only in the guard after both updates; queued work after a fault is a no-op and
physical work counts only completed paired updates. Scratch references/norms are
reinitialized per window; complete persistent checkpoints remain authoritative.
Only the scalar correction control predicts a next-window budget from the prior
window maximum: centered increments reset at the boundary, so that maximum is
not a sound predictor of the next window's increment size.

Use power-of-two row equilibration, carrying exact scale mappings for the original
primal/dual endpoint and bounds. Matched native and candidate use the same scaled
model, initial state, fixed stable step and audit controller. Study scaling and
encoding corrections as separately labeled development ablations. Known fixture
solutions are never used as initial iterates. Original-A FP64 audits and the
independent checker retain the unscaled model as authority.

At most 32 updates are submitted together, with original-model audits separated
by no more than 200 accepted updates. Shorten intervals near final accuracy or
the local noise floor. Retain monotone physical work, deadline, generation and
solve identities. Complete rollback restores packed and correction state and
controller checkpoint. Numerical safety failures restore and promote x2 -> x4
-> native. A finite, fully completed candidate at a local/projection guard may
first receive independent original-model final checking. If it certifies, it is
a terminal result, never an adopted failed checkpoint. Otherwise recovery is
mandatory; nonfinite failure never takes this shortcut. A failed conversion goes
directly to native; native failure stops.
Cancellation is terminal and cannot adopt unchecked state. The local allowance is `max(final_tolerance,min(1,last_original_residual)) *
state_scale / 8`: a one-eighth operational error budget, separately versioned from
the conservative one-sixty-fourth development setting. It is not a certification
tolerance or a proved global remainder. Local estimates remain
operational and are never called proved enclosures. The old per-window 10% slope
cliff is replaced by sustained absence of progress coupled to observed local
error; slow monotone progress alone does not force precision escalation.

A structurally zero column with an improving unbounded direction can terminate
with an explicit nonoptimal refusal, not a finite optimum or an unboundedness
certificate without established primal feasibility.

## Delivery and performance contract

Move numerical orchestration into the Rust service. Retain immutable original
model bytes/hash, parsed checker model, matrix/operator preparation and reusable
GPU buffers, while resetting every numerical/controller state between solves.
The checker is an independent CPU process and receives only the original model
and actual endpoint. Compact source-bound receipts retain replayable endpoints;
avoid redundant model JSON generation and detailed evidence on every audit.
For at least 4096 nonzeros, evaluate independent certificate columns on four CPU
workers, concatenate in original column order, and reuse the exact original
outward arithmetic and final reduction tree. Preserve first-refusal order and
require bit-for-bit differential checks against serial `optimizer_lp::certify`.
Original feasibility and gap functions are unchanged. This is scheduling of the
same certificate, not a replacement numerical criterion.
Count all startup, preparation, correction, checking, export and durable delivery
cost. Cold and prepared costs and startup amortization stay separately labeled.

Native controls receive the same host optimizations and stable recurrence. An
automatic choice may select native for sparse/small workloads and corrected FP4
for favorable dense workloads only under an explicit source-bound policy; label
actual arithmetic work and fallback. GPU event time alone is not a solve speedup.

Admission order: CPU model/encoding/scaling/checkpoint/controller tests and build;
independent actual-instruction/product/trajectory comparisons; lifecycle,
cancellation, generation, budget and conversion failures; memcheck, racecheck,
initcheck and synccheck; then a newly frozen matched solve cohort. Larger generic
dense fixtures must have nontrivial solution significands, not only the previous
eighth-integer targets. Include the ill-scaled and intentional refusal families.
Development ablations may be iterated with immutable attempts and all charges.
Formal manifests bind exact settings, source, device, deadlines and all cells
before execution, with no automatic scientific retry. Report uncertainty,
coverage, complete latency, kernel costs, correction/fallback and negative results.
Retain the 1.10x cold model-median geometric mean/no-regression/no-coverage-loss
criterion for any proposed retained preset; prepared wins are separately labeled.

## Independent resources

New ceiling: 160000 CPU / 24000 GPU seconds. CPU phases: implementation 48000
(including 512 preparation), native 16000, acceptance 40000, study 40000,
reporting 12000, cleanup 4000. GPU: acceptance 8000, study 16000. Four CPU slots,
one shared pinned SM120 lease, 16 GiB sampled aggregate RSS and 12 GiB device
buffers, unchanged in-container supervisor. Whole reservations must fit; failed
and unsettled jobs keep full charges. Artifacts: `artifacts/gpup-fp4-accel-v1`.
No historical transfer, public default change, GPUP-8 retry or GPUP-9 release.
Commit locally after delivery; no push/publication.

## Separate cold EOF delivery comparison

After the completed 1440-cell v1 cohort, its cold adapter is observed to quantize
completion in approximately 50 ms steps: Python's timeout wait polls a child
whose stdout was redirected to a file. Preserve that complete-cost result exactly.
A separate `cold-eof-v1` cohort changes only delivery: wait on stdout/stderr pipe
EOF, retain the same 35-second outer deadline, then durably write exact response
and log bytes. Process startup, exit, preparation and all checking remain inside
the timer. CPU tests verify exact delivery and timeout refusal first.

Freeze 360 new cells: the same twelve model bytes, two tiers, five repetitions
and cold order, for nativefast/gridfp4x2/auto. Numerical sources, device image,
settings, original certification and retention criteria are unchanged. Require
identical endpoints, certificates and physical work to each corresponding v1
cell; reuse the serial replay only by exact identity. Preserve both cohorts,
including all costs/failures. This is an explicit delivery optimization within
the active allocation, not a retry or replacement of any v1 scientific cell.
