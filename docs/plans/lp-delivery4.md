# GPUP-DELIVERY4: cold startup and lifecycle costs

Status: recommended next task; execution and allocation not released
Evidence: [DELIVERY3 diagnosis](../benchmarks/lp-delivery3-diagnosis.md)
Dependency: GPUP-DELIVERY3 complete

The selected strict dense512 cold route spends about 371 ms in session setup and
112–114 ms outside setup/solve, versus only 4.5–5.4 ms in GPU event intervals.
The dense cold arithmetic-only ideal bound is 1.0094x. Prioritize those lifecycle
costs before another mixed-precision cold experiment.

## First slice: attribution and a concrete optimization proposal

1. Bind an isolated executor and original models/evidence. Begin CPU-only:
   separately measure model read/hash/JSON decoding, LP/checker plan construction,
   solver representation/scaling and executable/model readiness hashing. Keep
   exact validation order, representations and provenance as acceptance contracts.
2. Before any new device work, supply a separate bounded resource manifest and
   freeze a small lifecycle measurement protocol. Instrument process entry,
   response construction/serialization, owned buffer/module/context destruction,
   checker EOF/reaping, parent collection and durable writes. Explicitly account
   for the current 112–114 ms outer remainder. Do not call it CUDA teardown based
   solely on subtraction. Report instrumented and uninstrumented boundaries.
3. Assess reducing or overlapping the serial host preparation (about 125 ms in
   two diagnostic blocks) with checker/device startup. Treat critical-path savings
   and contention as hypotheses. Preserve early input refusal, independent
   original-model checking, process ownership and complete failure cleanup.
   Do not weaken hash binding or move destruction outside the cold timer.
4. Rank measured opportunities and choose one concrete change. An additional
   repeated hashing optimization already hidden behind CUDA startup may give no
   complete-time gain. New code belongs in a separate research package; original
   implementations and all failed attempts remain exact.

## Conditional later admission

Run CPU exact differentials before device lifecycle/failure admission. If any
kernel/source image changes, obtain new appropriate device/sanitizer acceptance;
unchanged source-bound admission may be reused only with explicit verification.
A cold confirmation must use a new frozen schedule, same-quality strong native
and FP4 controls, all declared family guards, complete EOF/durability costs and
prospective uncertainty rules. Prepared throughput and amortization are separate.
No confirmation sample count or budget is implicitly inherited from DELIVERY3.

MIXED2 remains an independent prepared dense alternative. Before device admission
it still owes a CPU numerical contract, actual matrix-only accelerated fraction,
work multipliers, added conversion/guard/recovery costs and a viable scoped total-
time case. The whole-event 2x prepared forecast is not that admission.

This plan specifies the next work, not its execution release. No new solver or
GPU run, public preset, TENSOR2 release or GPUP-9 release occurs in the diagnosis.
