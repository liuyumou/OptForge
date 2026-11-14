# MIXED2 independent confirmation

[SPEC-0040](../specifications/SPEC-0040-mixed2-confirm.md) / [ADR-0073](../decisions/ADR-0073-mixed2-confirm.md).

Status: **incomplete-confirmation**. **324 / 512 sessions**, **10368 certified solves**.
All 32 planned blocks were attempted; 24 blocks have resource refusals. There are 188 missing complete-session cells and 280 retained responses outside complete sessions.
The scoped value criterion passes in 0 of eight family/tier comparisons; 0 pass the separate provisional 1.10x lower-bound comparison.
Resource refusals prevent a complete-coverage or adoption pass. Intervals below describe
available complete pairs conditional on observed coverage; missingness may be informative.
These observations must not be presented as confirmed speedups.
This independent cohort uses the unchanged scenario-reuse executable and CUDA image.
Earlier incomplete cohorts, sources, decisions and closed charges remain exact; no pooling or retry.
Public defaults remain unchanged. These constructed workloads do not establish production adoption.

## Complete session results

Each fresh session cycles four original-model RHS/objective scenarios eight times. The endpoint
includes parsing, independent checker/cache/representation setup, model switching, all 32 solves,
original-model certification, durable responses, EOF and destruction. FP64 state resets each solve.
Native and FP4 receive the same delivery, preparation overlap and CPU placement.

| Family | Tier | Available pairs | Native ms | FP4 ms | Paired speedup [simultaneous interval] | Saved ms [interval] | Scoped criterion |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| dense-coupled-1024 | certified-1e-7 | 21 | 5097.446 | 4852.696 | 1.050 [1.033, 1.067] | 242.766 [163.058, 318.276] | not established |
| dense-coupled-1024 | certified-1e-9 | 21 | 6132.186 | 5763.325 | 1.067 [1.046, 1.077] | 385.675 [268.666, 440.600] | not established |
| dense-coupled-2048 | certified-1e-7 | 15 | 15793.651 | 15194.049 | 1.039 [1.028, 1.056] | 594.469 [424.737, 838.962] | not established |
| dense-coupled-2048 | certified-1e-9 | 18 | 18730.774 | 17985.537 | 1.041 [1.038, 1.056] | 727.687 [674.953, 997.008] | not established |
| dense-generic-1024 | certified-1e-7 | 20 | 2959.978 | 2894.811 | 1.013 [1.000, 1.036] | 38.903 [0.145, 105.118] | not established |
| dense-generic-1024 | certified-1e-9 | 20 | 2954.190 | 2941.007 | 1.012 [0.989, 1.023] | 35.493 [-33.326, 67.084] | not established |
| dense-generic-2048 | certified-1e-7 | 20 | 9594.894 | 9519.735 | 1.007 [0.997, 1.027] | 64.233 [-31.402, 249.810] | not established |
| dense-generic-2048 | certified-1e-9 | 21 | 9561.957 | 9538.175 | 1.002 [0.989, 1.017] | 23.016 [-111.755, 164.010] | not established |

The frozen seed is 400073: 32 blocks, balanced 16/16 lane order for every family/tier.
Exact binomial median intervals cover eight paired ratios and eight absolute savings using
Bonferroni alpha 0.05/16. For the planned complete 32-block comparison, rank 8 gives at least 95%
simultaneous coverage conditional on independent blocks; at least 25 blocks must exceed a threshold
for its lower bound to exceed that threshold. Available-pair intervals use their actual retained count.
Within-session solves are not independent samples. Marginal medians need not divide to the paired ratio.
Shared GPU/host activity and temporal dependence limit the statistical interpretation.
The predeclared scoped criterion requires complete coverage, every original-model certificate,
ratio lower bound above 1.0 and savings lower bound above 10 ms per session (0.3125 ms/request).
That absolute floor is exploratory workload value, not a production SLO. The separate 1.10x
comparison remains provisional. Every block, first-16 sensitivity and order split is retained.

## Measured costs and remaining work

| Family / tier | Native / FP4 setup ms | Native / FP4 request ms | Native / FP4 GPU phase ms | Native / FP4 physical updates per request |
| --- | ---: | ---: | ---: | --- |
| dense-coupled-1024 / certified-1e-7 | 1630.382 / 1685.576 | 102.488 / 93.170 | 28.346 / 17.857 | [600] / [600] |
| dense-coupled-1024 / certified-1e-9 | 1628.981 / 1682.971 | 134.049 / 121.572 | 37.796 / 23.807 | [800] / [800] |
| dense-coupled-2048 / certified-1e-7 | 6014.957 / 6212.179 | 294.151 / 269.223 | 52.895 / 28.011 | [600] / [600] |
| dense-coupled-2048 / certified-1e-9 | 6002.357 / 6193.438 | 387.360 / 357.370 | 70.534 / 37.342 | [800] / [800] |
| dense-generic-1024 / certified-1e-7 | 1636.353 / 1671.863 | 36.115 / 33.144 | 9.448 / 5.950 | [200] / [200] |
| dense-generic-1024 / certified-1e-9 | 1628.152 / 1714.978 | 36.086 / 33.145 | 9.447 / 5.950 | [200] / [200] |
| dense-generic-2048 / certified-1e-7 | 6016.203 / 6203.610 | 99.979 / 93.154 | 17.633 / 9.338 | [200] / [200] |
| dense-generic-2048 / certified-1e-9 | 6003.294 / 6195.236 | 100.170 / 93.120 | 17.631 / 9.339 | [200] / [200] |

Setup is per session; request and nested GPU times are medians per solve. Brackets list
the distinct observed physical update counts, including correction work.

For strict coupled2048, aggregate complete-session cost shares are:

- fp4x2: setup 34.2%, independent checker 46.0%, original audit 8.4%, iteration 7.0%.
- native: setup 31.7%, independent checker 43.9%, original audit 8.0%, iteration 12.1%.

These are nonoverlapping host-clock partitions. GPU event diagnostics are nested and must not
be added to them; they include submitted windows and host/launch gaps, not isolated tensor throughput.
Preparation and independent checking remain candidates for exact-cost reduction. Removing either
in a forecast would not establish an attainable speedup. Generic and coupled families remain separate;
small-family historical regressions and cold-solve findings are unchanged. No universal preset follows.

## Supervision diagnosis and limitations

The historical guardian tested receive freshness before draining queued sample messages. A controlled
180 ms guardian pause reproduced its refusal while the sampler remained healthy (maximum gap 5.858 ms).
The isolated correction drains the queue first and validates monotonic sample timestamps. Queued
stale traffic cannot renew freshness; malformed, discontinuous, stalled or dead streams still refuse.
Resource, cadence, death, deadline and cleanup checks remain exact apart from notification placement
and an added 100 ms scan-duration guard. The sampler publishes its start timestamp at the start
of scanning. The earlier correction published it afterward: two valid 60 ms scans could then cause
a false stale notification. The controlled boundary probe reproduces that refusal; the final version
passes with a 66.885 ms maximum cadence and 61.823 ms scan work. A 150 ms scan still refuses,
including the terminal scan when the guardian is delayed. A progress notification never grants a pass.
All 36 contracts pass, including live delay/stall, resource, cancellation, transport and cleanup cases.
This is evidence for the observed design defect and tested correction, not the cause of old failed instants.

Three native attempts refused notification freshness, including with lower worker priority and separate
Rust-worker placement. They do not establish that actual sampling cadence exceeded 100 ms. The first guardian
continued observing (maximum loop gap 11.714 ms), so the queue-order correction alone is not universal
availability. All failed reservations and partial logs are retained. A separate instrumented three-worker
diagnostic passed all 72 experiment-library tests, and a traced full native gate passed on the intermediate
source. Final admission reruns the complete gate without tracing on the final source. It restricts Rust workers
to three CPUs and lowers worker priority while keeping four CPUs for nested Python resource contracts. Scientific
sessions retain the prior three-worker / fourth-control-CPU placement and normal priority.
Across this cohort, maximum reported sampler gap is 96.916 ms, scan work 86.758 ms, guardian loop gap 40.026 ms, and sample delivery lag 17.395 ms.
These are separate timer boundaries. Sampler-work and RSS maxima use completed coordinator reports;
refused runs retain guardian observations and may lack terminal sampler metrics.
Admission passes did not establish uninterrupted availability
for the frozen cohort. Its refusals remain binding, with all partial outputs and full charges retained.
The observed control stalls are not assigned to a kernel, scheduler or memory cause without evidence.
Further confirmation should follow low-disturbance sampling-phase and scheduling diagnosis; another
repeated cohort is not a substitute for resolving this operational limitation.
Coarse temperature, clock, power and utilization observations are retained without exclusions or causal claims.

## Acceptance and reproducibility

Full native gate: 638 repository Rust / 742 Python tests, 28 isolated Rust tests, Clippy, dependency
audit, committed-record replay, artifact/documentation validation and smoke. Fresh same-image admission
compares 64 smoke and 512 full-pilot outputs exactly with original scenario results. Prior device and
four-sanitizer arithmetic and scenario-switch admissions are reused only for the unchanged source/image.
The original independent serial checker reassesses all retained unique final and audit endpoint/tier pairs.
Six analysis-corruption guards reject changed work, configuration, response bytes, original authority,
cost partitions and duplicate cells; resource failures or missing sessions suppress the coverage decision.
The first supervisor contract run exposed a reason-string compatibility mismatch; its full failed charge
and source are retained. No scientific cell is retried.

[Analysis](data/mixed2-confirm-analysis-v1.json), [diagnosis and block ledger](data/mixed2-confirm-diagnosis-v1.json),
[portable response archive](data/mixed2-confirm-records-v1.json).
Replay: `python3 tools/lp_mixed2_confirm_analysis.py verify`.
GPUP-8 remains incomplete and GPUP-9 gated. No follow-on execution or allocation is released.

## Post-cohort CPU diagnosis

The admitted post-refusal recorder collects process state and requests a Python stack only after
the guardian has already decided to refuse. Two controlled contracts verify that refusal and
cleanup remain intact. It adds no per-sample tracing; signal capture is not a complete kernel trace.

| Probe | Result | Reason | Peak sampled RSS MiB |
| --- | --- | --- | ---: |
| hash-whole-v1 | passed | completed | 303.6 |
| hash-streaming-v1 | passed | completed | 80.4 |
| cpu-library-observation-v1 | refused | lost_coordinator_heartbeat | unavailable |
| cpu-library-observation-v2 | refused | lost_coordinator_heartbeat | unavailable |

Both hashing paths check all 20 original model hashes for 12 rounds. Hashing alone did not reproduce
the refusal. Their fixed order and different memory behavior do not establish a causal performance
improvement or a remedy for the frozen failures. The CPU experiment workload does reproduce the
progress refusal, so GPU execution is not a necessary trigger.
At the first post-refusal observation the coordinator is marked runnable; no Python stack arrives
during the requested 15 ms capture sleep. A versioned follow-up records scheduler counters and
pending signals before and after that sleep. These observations retain their capture delay and
do not by themselves assign a scheduler, memory or kernel cause.
[Post-cohort observations and capture records](data/mixed2-confirm-postdiagnosis-v1.json).

For cpu-library-observation-v2, the enclosing observations are 43.981 ms apart; scheduler counters unchanged: True. The captured status retains the pending-signal masks and the stack file retains its partial output. This is consistent with delayed execution, not a complete attribution of the earlier failed interval.

Independent serial checking covers 11224 response files / 36312 assessments / 144 distinct endpoint/tier pairs. Every retained numerical trajectory matches admission exactly; final/audit endpoints and original certificate bytes match the admitted set. Portable replay passes without the original artifacts tree; all 2018 historical files and previous handoff/backlog entries remain exact.

The first final CPU verification also refused notification freshness. Its full reservation,
source and capture are retained. The post-refusal stack identifies the coordinator's 5 ms pidfd
wait; the runnable-state observations and unchanged scheduler counters bracket about 24.745 ms.
The capture occurs after refusal and does not establish where the entire missed interval was spent.
Portable replay and final aggregation therefore settle as separate CPU verification steps, with
all source and artifact bindings checked and lower-priority verification workers. A separate
packaging attempt failed because hardlinks crossed filesystems; the corrected helper retains
the copy fallback. Its failed source and full reservation remain recorded. No scientific cell
or timing decision is retried. A later staging check caught an extra trailing blank line in
the report helper; its failed source and full charge are retained, with formatting corrected.
[Closing verification diagnosis](data/mixed2-confirm-closing-diagnosis-v1.json).

Allocation closed at 58479.574258236 CPU / 6668.617079311 GPU seconds, including 128 closing CPU seconds. All 33 failed reservations retain full charges and sources; cleanup is empty. Historical funding transfers: zero.
[Acceptance](data/mixed2-confirm-acceptance-v1.json), [accounting](data/mixed2-confirm-accounting-v1.json),
[development evidence](data/mixed2-confirm-evidence-v1.json), [complete resource receipts](data/mixed2-confirm-resources-v1.json.gz).

Closing metadata validation recovered from an unavailable YAML import using exact standard-library backlog checks; the failed script and full closing reserve remain preserved. [Closing administration](data/mixed2-confirm-closing-admin-v1.json).
