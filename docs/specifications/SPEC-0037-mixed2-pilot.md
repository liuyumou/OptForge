# SPEC-0037: MIXED2 prepared attribution and GPU storage pilot

The user authorizes the recommendation to separate pilot admission from adoption
and explicitly permits GPU studies. [ADR-0070](../decisions/ADR-0070-mixed2-pilot.md)
changes prospective policy only. Historical SPEC-0036 records and criteria stay exact.

## Decision stages and scope

Pilot admission requires a useful attribution question, exact native contracts,
bounded resources and safety. It does not require a predicted 1.10x improvement.
The provisional 1.10x adoption target remains for a later complex numerical
candidate, with unchanged independent original-model 1e-9 authority and coverage.
Before that later confirmation, justify practical value using target request
volumes, absolute latency saved, lifecycle and implementation cost, and plan
sample size against plausible effects and observed block variability. No adoption
threshold or power is inferred from eight pilot blocks, and no default changes.

Measure the actual native prepared path and quantify profiling disturbance.
Use a separate research package based on DELIVERY4's exact model/checker/solver
body, with admitted batching and overlap enabled equally in both configurations.
Control uses retained native CUDA kernels. Profile adds a new instrumented copy
of grid_native, four per-CTA globaltimer observations around the matrix loop and
reduction, and bounded per-launch CUDA events. Original arithmetic, ordering,
checkpoints, audits, work, certificates, independent checker and signed zeros must
match retained originals. Sparse nativefast lanes keep their original kernels;
uninstrumented components remain explicitly unattributed.

Software timestamps are diagnostic, target-specific observations. Report matrix
interval unions and complete CTA interval unions across concurrent CTAs, never
sum overlapping CTA times. Keep CUDA event time, software timestamp coverage,
launch gaps, host costs, setup and teardown distinct. Report timer granularity
and control/profile overhead. Do not call instrumentation-free matrix duration
identified if profiling materially changes execution. Include profiler cost in
profile complete time; control remains the complete-cost baseline.

Separately benchmark FP32 storage widened to FP64 FMA against FP64 storage with
identical eight-warp product/reduction and fixed, nonzero input vectors, both
A and transpose. Use original unscaled matrices (identity scaling), including
padding and sparse-tail shapes. Measure host representation construction, H2D,
D2H and stream-batch event time. A separate conservative original-to-FP32 product
error guard uses upward FP64 arithmetic; its cost and extra storage stay visible.
Check native and represented products bitwise against a CPU schedule oracle and
all guarded outputs against independent exact-rational original dots, including
subnormals, cancellation and edge shapes. No FP32 state or approximate certificate.
This is a product-cost pilot, not a mixed solver: progress, useful accepted mixed
windows, work amplification and complete recovery costs remain unmeasured.

## Ordered admission and immutable pilot

First CPU build/tests, exact checker/model comparisons and the full native gate.
Then new-image GPU arithmetic/lifecycle admission, including cancellation,
checkpoint restore, setup refusal and final original certificates. All four
scoped Compute Sanitizer tools must pass on the new kernels/image before timings.
Record source, compiler, executable and image identities. Preserve failed sources
and full reservations. Development repairs use new identities; frozen scientific
cells are never retried automatically.

After admission freeze eight new independent blocks, all twelve retained model
families, nativefast at certified-1e-9, paired control/profile and three fresh
cold-iterate solves per prepared session: 192 sessions / 576 solves. Pair order
is balanced 4/4 per family; randomize family order with seed 370070. All eleven
bounded families must certify and the intentional unbounded refusal stays visible.
Record complete per-solve delivery through durable output, setup, teardown and
per-solve numerical/work identity. No cold speedup claim or held-out adoption.

A second independent product cohort uses eight blocks, dense128/256/512 and
irregular33, both directions and three modes (FP64, FP32, error guard): 192 cells,
128 launches per cell, randomized mode order with seed 370071. All products use
the same documented generic nonzero RHS, not timing-selected operands. Report
all cells, individual ratios and descriptive block uncertainty; no retained
speedup is declared. Keep the full event-based forecast as an upper-bound case,
then narrow only what the measurements actually identify. Use multiple workload
and lifecycle scenarios, including all measured preparation/transfer/guard costs.
A pilot can finish with a negative or inconclusive result and no solver release.

## Independent allocation and delivery

Ceiling 48000 CPU / 2400 GPU seconds. CPU: implementation 12000 (512 preparation),
native 8000, acceptance 12000, study 10000, reporting 4000, cleanup 2000 (128 closing).
GPU: acceptance 1200, study 1200. Four CPU slots, 16 GiB sampled RSS, 12 GiB owned
device buffers, one pinned shared SM120 lease, unchanged in-container supervisor.
Whole jobs must fit; failed reservations stay fully charged. Receipts:
artifacts/gpup-mixed2-pilot-v1. All historical allocations remain closed.

Publish durable positive, negative and inconclusive findings, source-bound raw
portable evidence, reproduction, exact historical preservation, software/device
acceptance and final charges in [the report](../benchmarks/lp-mixed2-pilot.md).
Commit locally only; no publication, default change, historical regrading,
GPUP-8 completion or GPUP-9 release. This allocation covers the diagnostic pilot,
not a subsequent mixed solver or adoption confirmation.
