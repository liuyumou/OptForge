# SPEC-0033: Bounded independent-checker delivery

Status: implementation, 2026-11-12
Owner: experiment tooling
Decision: [ADR-0065](../decisions/ADR-0065-delivery2.md)

## Contract

GPUP-DELIVERY2 is an isolated delivery variant of GPUP-FP4-CHECKER. Its selected
mechanisms are one serialized buffer per checker request/response and eager
independent checker preparation overlapping CUDA setup. The child reads exact
original model bytes independently. It retains no previous certificate or iterate.
Numerical modules, solver control flow, tiers, endpoint hashes, original-model
feasibility, dual-bound mathematics and conservative refusals stay unchanged.

A single executable provides matched sequential/unbuffered control via
`GPUP_DELIVERY2_CONTROL=1` and default batched/overlapped delivery. The control
retains the old request bytes. Runtime code remains safe Rust. Requests remain
JSON with round-trip binary64, including signed zeros; no quantization or changed
arithmetic is permitted. Each response is checked for model, endpoint, tier and
checker image binding. Failed connections are poisoned. Frames are capped at
8 MiB during reading, model input at 128 MiB; truncated frames are failures.
EOF releases the checker; failed setup owns a cleanup guard; the unchanged
bounded drop kills and reaps an unresponsive child. The external supervisor bounds
whole-job deadlines, CPU, sampled RSS and descendant cleanup.

## Admission and measurement

1. Unit tests verify exact serialized bytes and bit patterns, batching, frame
   limits, malformed requests and truncated streams. CPU process tests cover fresh
   certificates, malformed identity/tier/dimensions/status, changed endpoints,
   multiple requests, EOF and setup failure cleanup. Differential replay checks
   every retained FP4-ACCEL endpoint against its original serial receipt.
2. Run the full native repository gate and isolated crate format/lint/tests/build.
   Preserve all prior tracked files except navigation/handoff files. Archive each
   development source version and all failed reservations.
3. Bind the exact unchanged CUDA image and reuse its four-sanitizer admission only
   for that image. New smoke exercises both delivery modes, native and FP4 lanes,
   both tiers, bounded/refusal families and cancellation/failure behavior.
4. Freeze a new cohort after admission: the twelve FP4-CHECKER families, nativefast
   and gridfp4x2, two tiers, cold/prepared lifecycles, five paired repetitions and
   two delivery modes (960 cells). Alternate order by repetition; one service per
   family/mode for prepared solves, fresh reset each solve. Compare all numerical
   evidence and physical work with retained endpoints. No frozen cell retries.
5. Cold time includes startup, solve, independent checks, teardown and durable
   response/log writes. Prepared time includes each fresh solve, checks and durable
   response; setup/teardown are separately reported. No summed marginal medians.
   Retention requires >=1.10x cold model-median geometric mean, no certified model
   median regression or coverage loss, separately for each lane/tier. Report paired
   ranges and deterministic paired bootstrap 95% intervals (seed 33, 2000 draws).
   Refusals stay in coverage and out of certified speed ratios. Prepared results
   never substitute for cold retention. No public preset or GPUP-9 release.

## Independent allocation

32000 CPU seconds: implementation 8000 (including 512 preparation), acceptance
12000, study 8000, reporting 3000, cleanup 1000. Conditional GPU 1800 seconds:
acceptance 300, study 1500. Four CPU slots, 16 GiB sampled RSS, 12 GiB device buffers,
one pinned shared lease under the unchanged in-container supervisor. Whole jobs
must fit. Failed/unsettled reservations retain full charges. No historical transfer.
Artifacts: `artifacts/gpup-delivery2-v1`. Commit locally after delivery.
