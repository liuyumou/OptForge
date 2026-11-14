# Delivery overhead optimization — GPUP-DELIVERY2

Status: implemented; frozen comparison complete; broad retention fails
Date: 2026-11-12
Contract: [SPEC-0033](../specifications/SPEC-0033-delivery2.md)
Decision: [ADR-0065](../decisions/ADR-0065-delivery2.md)

DELIVERY2 batches independent-checker pipe transport and overlaps original-model checker preparation with CUDA setup in an isolated Rust executor. Strict dense-512 cold delivery improves about **1.40x** in both native and FP4 lanes. Broad cold geometric means improve 1.058–1.079x but fail the predeclared 1.10x/no-regression retention rule. Keep the supported native solver and public defaults unchanged.

## What changed

The retained executor serializes JSON directly into an unbuffered child pipe. The candidate serializes a borrowed request into one bounded buffer, then writes and flushes that buffer. Endpoint floats retain their exact binary64 values, including signed zeros. Responses use the same batching. The independent checker reads original model bytes itself and performs a fresh assessment for every request; no prior certificate or warm iterate is reused.

Independent checker startup now begins before CUDA context/module/stream setup, and the solver joins its readiness before any numerical work. The cold timer still charges both preparations and all process startup/teardown. CPU-only dense-512 checker setup takes approximately 194 ms in either delivery mode; overlapping it explains the observed roughly 200 ms cold setup reduction without claiming that this work disappeared.

The same executable provides the sequential/unbuffered control through `GPUP_DELIVERY2_CONTROL=1`. Both lanes use the unchanged device image and exactly the retained numerical state machine, controller, model preparation, final tiers and certificate arithmetic. The old executor and every prior result remain intact. This is a delivery comparison, not an FP4 arithmetic speedup claim.

Frames are bounded while reading, incomplete frames refuse, and failed response bindings poison the connection. Model, endpoint, tier and executable hashes are checked before accepting a certificate. A checker spawned before failed device setup remains owned by a cleanup guard. Failed cold delivery preserves partial stdout/stderr as evidence; it cannot become a successful result.

Implementation: [executor](../../research/lp-delivery2/src/main.rs), [transport](../../research/lp-delivery2/src/transport.rs), [study](../../tools/lp_delivery2_study.py), [CPU gate](../../tools/check_delivery2_cpu.sh).

## Complete comparison

All **960 cells complete**: twelve retained development families, nativefast/gridfp4x2, 1e-7/1e-9 tiers, two delivery modes, cold/prepared lifecycles and five paired repetitions. Eleven bounded families certify at both tiers: **880 certificates**. All 80 intentional infinite-bound/unbounded-direction cells remain refusals and stay in the coverage denominator. No scientific cell was retried.

Every endpoint, certificate, audit, checkpoint, recovery event and physical/logical work count matches its retained original. Floating-point comparisons preserve zero signs. Executable identity and measured timing fields are the only permitted differences.

Cold delivery runs a fresh worker and includes solve/checking, process exit, and fsynced response/log writes; request construction and analysis are outside the timed boundary. Prepared delivery starts after separately charged model/device setup, includes a fresh solve and fsynced response, and records teardown separately. There is one prepared session per family/mode, not five independent session replications. All work is within the new supervised allocation.

Ratios are control/candidate. Intervals use the predeclared 2000 within-model paired bootstrap resamples (seed 33) over five repetitions. They describe this constructed development cohort, not production or held-out generalization. Phase medians below are separate medians and are not an additive partition of median total time.

| Lifecycle | Tier | Lane | Geometric mean | Paired bootstrap 95% | Regressing model medians |
|---|---|---|---:|---|---:|
| cold | 1e-7 | native | 1.062273x | 1.030606–1.089582 | 4 |
| cold | 1e-7 | FP4 | 1.078861x | 1.049220–1.111122 | 1 |
| cold | 1e-9 | native | 1.058415x | 1.045118–1.098460 | 3 |
| cold | 1e-9 | FP4 | 1.066495x | 1.036134–1.095444 | 2 |
| prepared | 1e-7 | native | 1.048812x | 0.872951–1.402871 | 3 |
| prepared | 1e-7 | FP4 | 1.107911x | 0.906441–1.162112 | 2 |
| prepared | 1e-9 | native | 1.035397x | 0.943447–1.215604 | 3 |
| prepared | 1e-9 | FP4 | 1.048363x | 0.943048–1.150293 | 5 |

No cold lane/tier passes retention; all preserve certified coverage. Prepared intervals include parity, and prepared throughput cannot substitute for the failed cold decision.

## Dense-512 gains and prepared regressions

| Lifecycle | Lane | Control total ms | DELIVERY2 total ms | Control setup ms | DELIVERY2 setup ms | Control checker ms | DELIVERY2 checker ms |
|---|---|---:|---:|---:|---:|---:|---:|
| cold | native | 700.889 | 500.806 | 567.612 | 367.144 | 6.230 | 6.720 |
| cold | FP4 | 710.809 | 509.217 | 571.485 | 367.952 | 6.280 | 6.833 |
| prepared | native | 22.275 | 24.228 | 581.407 | 384.581 | 5.985 | 4.962 |
| prepared | FP4 | 20.216 | 21.362 | 581.407 | 384.581 | 6.224 | 4.861 |

Both dense lanes perform exactly 200 updates. Strict cold native improves 700.889 to 500.806 ms (1.3995x; observed paired range 1.3826–1.4016). FP4 improves 710.809 to 509.217 ms (1.3959x; paired range 1.2568–1.5338). These gains apply to this dense family; smaller models do not amortize the same preparation.

Prepared strict dense-512 total time regresses: native 22.275 to 24.228 ms, FP4 20.216 to 21.362 ms, despite lower checker phase medians. No causal claim is assigned to the other phase variation. Retain these unfavorable observations and the broad uncertainty; there is no scientific rerun to obtain a better result.

## CPU transport mechanism

All 102 retained unique endpoints receive five fresh assessments through each transport mode, for 1020 fresh CPU certificates matching the original serial receipts. Median-of-endpoint-medians for accepted strict endpoints:

| Family | Control round trip ms | Batched round trip ms |
|---|---:|---:|
| coupled-equality | 0.358 | 0.130 |
| dense-generic-128 | 0.972 | 0.476 |
| dense-generic-256 | 2.136 | 1.176 |
| dense-generic-512 | 5.383 | 3.578 |

These CPU-only round trips include IPC and fresh assessment; they exclude model/checker startup. The dense-512 ratio is about 1.50x. This mechanism measurement does not override the actual complete-solve results.

## Acceptance and preservation

The full native gate passes **638 Rust and 653 Python tests**, native HiGHS, Clippy/format/build/docs, dependency policy, artifact validation, committed-record replay and CPU smoke. The isolated DELIVERY2 package passes **24 Rust tests** and its release build/lint. The final four focused Python guards include a new partial-transcript regression added after the full gate; 654 distinct Python tests are covered across those runs.

CPU process admission includes 20 cases across both modes: fresh terminal eligibility, EOF, wrong model/dimensions/status/tier, duplicate fields, truncation, oversize frames and missing-model setup. Device admission passes **84 lifecycle cases**, one failed-module startup cleanup case, and **32 matched integration cells**. Cancellation, rollback, fresh solves, fault recovery, stale state and physical work accounting remain exact. The original four-sanitizer admission is reused only for the unchanged source-bound device image; no new sanitizer run is claimed.

All **1666 historical tracked files** outside the four navigation/handoff files remain byte-exact, and older dated handoff text is unchanged. The numerical state-machine body is byte-exact. All new cell evidence is retained in a portable [compressed archive](data/delivery2-evidence-v1.json.gz), with [results, source bindings and intervals](data/delivery2-result-v1.json).

The first full software gate used an older virtual environment missing numpy/fastjsonschema; its six Python import errors, source snapshot and full **4000 CPU-second** reservation remain preserved. The corrected gate uses the previously accepted complete environment. No numerical source changed in response and no scientific cell was retried. A permission-review timeout prevented one launch before process creation; the permitted retry launched the sole cohort. A reporting CLI syntax refusal occurred before reservation; both prelaunch events are charged within the 512-second preparation allowance.

The independent ceiling is **32000 CPU / 1800 GPU seconds**, four CPU slots, sampled 16 GiB host RSS, bounded 12 GiB device buffers and one pinned shared GPU lease. RSS monitoring is cooperative, not hard cgroup containment. Historical allocations remain closed and no funds transfer occurs. Closed charge: **7489.258294208 CPU / 231.550283498 GPU seconds**, including the failed reservation and 128 closing-administration CPU seconds. Every supervisor cleanup is empty. [Acceptance](data/delivery2-acceptance-v1.json), [exact history](data/delivery2-history-v1.json) and [final accounting](data/delivery2-accounting-v1.json) retain the receipts.

## Handoff

GPUP-DELIVERY2 is implemented and its bounded comparison is complete. Dense cold setup improves substantially; the broad retention rule fails and prepared total gains remain inconclusive. Preserve the opt-in research executor and supported native control. No public preset, TENSOR2 campaign, GPUP-8 completion or GPUP-9 release follows.
