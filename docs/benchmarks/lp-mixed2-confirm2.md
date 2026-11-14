# MIXED2 complete independent confirmation

[SPEC-0041](../specifications/SPEC-0041-mixed2-confirm2.md) / [ADR-0074](../decisions/ADR-0074-mixed2-confirm2.md).

Status: **complete-confirmation**. **512 / 512 complete sessions and 16384 certified solves**.
All 32 blocks are retained; 0 resource refusals and 0 missing complete-session cells.
The predeclared scoped value criterion passes in 5 of eight family/tier comparisons; 0 pass the separate provisional 1.10x lower-bound comparison.
Public solver defaults remain unchanged. The constructed four-scenario streams do not establish production adoption.

## Complete session results

Each fresh session cycles four original-model RHS/objective scenarios eight times. The complete
endpoint includes parsing, checker/cache/representation setup, model switching, all 32 solves,
independent certification, durable output, EOF and destruction. FP64 state resets each solve.
Native window32 and FP4x2 window16 use the unchanged admitted numerical executable/image.
Both lanes receive the same preparation overlap, delivery and three-worker CPU placement.

| Family | Tier | Native ms | FP4 ms | Paired speedup [simultaneous interval] | Saved ms [interval] | Scoped value |
| --- | --- | ---: | ---: | --- | --- | --- |
| dense-coupled-1024 | certified-1e-7 | 5094.341 | 4857.438 | 1.0506 [1.0432, 1.0585] | 246.163 [209.503, 280.377] | passes |
| dense-coupled-1024 | certified-1e-9 | 6112.664 | 5744.689 | 1.0651 [1.0574, 1.0706] | 374.508 [330.955, 405.901] | passes |
| dense-coupled-2048 | certified-1e-7 | 15721.555 | 15154.267 | 1.0367 [1.0325, 1.0412] | 559.042 [494.213, 624.595] | passes |
| dense-coupled-2048 | certified-1e-9 | 18771.769 | 17898.363 | 1.0489 [1.0402, 1.0541] | 874.323 [718.962, 966.019] | passes |
| dense-generic-1024 | certified-1e-7 | 2943.976 | 2904.425 | 1.0135 [1.0001, 1.0287] | 39.168 [0.396, 82.724] | not established |
| dense-generic-1024 | certified-1e-9 | 2972.133 | 2893.847 | 1.0214 [1.0082, 1.0410] | 61.130 [23.824, 115.704] | passes |
| dense-generic-2048 | certified-1e-7 | 9576.549 | 9541.672 | 1.0057 [0.9975, 1.0181] | 53.625 [-24.012, 173.083] | not established |
| dense-generic-2048 | certified-1e-9 | 9573.809 | 9517.587 | 1.0045 [0.9991, 1.0142] | 43.229 [-8.262, 132.889] | not established |

Frozen seed 410074; 32 blocks, balanced 16/16 lane order per family/tier.
Exact binomial median intervals use Bonferroni alpha 0.05/16 across eight paired ratios and eight
absolute savings. Rank 8 gives at least 95% simultaneous coverage conditional on independent blocks;
at least 25/32 blocks must exceed a threshold for its lower bound to exceed that threshold.
Within-session solves are not independent samples. Shared host/device activity and temporal
dependence limit the interpretation. Marginal medians need not divide to the paired speedup.
The scoped criterion requires full coverage, original-model certificates, ratio lower bound above
1.0 and savings lower bound above 10 ms/session (0.3125 ms/request). This exploratory value floor
is not a production SLO. The separate 1.10x comparison is provisional. All block, pair-order and
first-16 sensitivity results remain in the machine-readable analysis. No old data are pooled.

## Measured cost partitions

| Family / tier | Native / FP4 setup ms | Native / FP4 request ms | Native / FP4 GPU phase ms | Native / FP4 physical updates |
| --- | ---: | ---: | ---: | --- |
| dense-coupled-1024 / certified-1e-7 | 1616.430 / 1699.241 | 102.345 / 92.817 | 28.349 / 17.855 | [600] / [600] |
| dense-coupled-1024 / certified-1e-9 | 1632.253 / 1663.516 | 134.074 / 121.280 | 37.799 / 23.808 | [800] / [800] |
| dense-coupled-2048 / certified-1e-7 | 6014.432 / 6217.441 | 292.442 / 269.331 | 52.902 / 28.012 | [600] / [600] |
| dense-coupled-2048 / certified-1e-9 | 6013.332 / 6212.669 | 387.698 / 355.280 | 70.530 / 37.345 | [800] / [800] |
| dense-generic-1024 / certified-1e-7 | 1616.484 / 1672.153 | 35.979 / 33.100 | 9.449 / 5.951 | [200] / [200] |
| dense-generic-1024 / certified-1e-9 | 1656.302 / 1662.015 | 36.150 / 33.102 | 9.449 / 5.951 | [200] / [200] |
| dense-generic-2048 / certified-1e-7 | 6009.495 / 6218.440 | 100.475 / 92.960 | 17.632 / 9.339 | [200] / [200] |
| dense-generic-2048 / certified-1e-9 | 6004.302 / 6207.078 | 100.106 / 92.590 | 17.633 / 9.339 | [200] / [200] |

Setup is per session; request and nested GPU times are medians per solve. Updates include
correction work. Lower GPU time alone does not establish a complete-session benefit.

## Performance diagnosis and limits

Strict coupled2048 GPU phase time falls from 70.530 to 37.345 ms/request (1.889x), while both lanes retain [800] physical updates per request. Complete-session medians fall from 18.772 to 17.898 seconds; the paired median gain is 1.0489x.
In aggregate FP4 complete-session cost, independent checking occupies 46.00%, setup 34.31%, audit 8.36% and iteration 6.93%. These disjoint host spans explain why the larger GPU gain produces a modest delivered gain. Nested GPU time is not added again.
Strict coupled2048 setup medians are 6013.332 ms native and 6212.669 ms FP4. This is an observed complete setup difference, not isolated attribution to representation construction. Scenario switching is only about 0.146 ms/request in the FP4 lane.
All 7372800 physical updates and 64 distinct final model/tier endpoints are retained. No recovery event occurs in this cohort; that does not establish recovery behavior outside these admitted streams.
All four coupled comparisons pass the scoped value criterion. Generic1024 at 1e-9 also passes;
generic1024 at 1e-7 has a ratio lower bound above parity but fails the 10 ms savings floor.
Both generic2048 intervals include parity. No comparison passes the provisional 1.10x lower bound.
The generic1024 tiers both take 200 updates and have nearly identical GPU phase times; their
different complete-session decisions do not establish a tolerance-dependent arithmetic effect.
The first-16 intervals for generic1024/1e-9 and coupled2048/1e-7 include parity, while their
predeclared full 32-block decisions pass. All first-16 medians and both pair-order medians remain
above parity, but these descriptive sensitivities do not establish temporal independence or a cause.
Further complete-cost work should target exact checker and preparation costs while preserving
original-model authority. These observations do not authorize a public preset or follow-on study.

## Sampling policy and diagnosis

The user authorized changing or waiving an inappropriate 100 ms limit. This
cohort adopts a **one-second maximum sampling gap, scan duration and heartbeat
freshness limit**, retains the 5–10 ms sampling target and records every observed
100 ms exceedance. Both lanes use the same policy and every elapsed delay remains
in the complete-session endpoint. The change is prospective: earlier 100 ms
refusals, their sources and full charges remain exact.

The original [ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md) threshold
was a resource-observation rule. It was not a numerical tolerance. RSS sampling
cannot enclose peaks between samples at either threshold. A one-second bound
accepts a longer possible observation gap; it does not guarantee continuous memory
enforcement. The 16 GiB sampled RSS stop, swap checks, four-CPU limit, 12 GiB
owned-device-buffer ceiling, independent death detection, wall budget and cleanup
remain in force. Per-process high-water observations supplement sampled RSS and
are not a true simultaneous aggregate peak.

The isolated supervisor is byte-exact with its predecessor after removing the
explicit policy, metadata and CLI changes. All 39 supervision contracts pass,
including a recorded 150 ms delay accepted under the new rule and a stall beyond
one second that still refuses and cleans up. The one-second limit is a finite
operational policy choice, not a scheduling guarantee derived from measurements.

Two fixed CPU experiment-library probes each pass all 72 tests. The first has a
13.397 ms maximum sample-start gap. The second reaches 97.715 ms, with an 81.685 ms
scan using 6.489 ms of process CPU. Shared-cgroup throttling counters increase by
ten events / 4.516513 seconds during the second probe. Neither reproduces an
actual interval above 100 ms. Wall time minus process CPU and aggregate shared
counters do not establish the cause of an individual interval or an old refusal.
Bounded in-memory phase tracing is diagnostic only and is absent from science.
Its exported summaries retain counts, extrema, the largest 32 spans per phase
and up to 4096 spans above 100 ms; they are not a complete raw scheduling trace.

Linux documents that [select timeouts may overrun due to scheduling](https://www.man7.org/linux/man-pages/man2/select.2.html).
The [kernel 5.19 cgroup documentation](https://www.kernel.org/doc/html/v5.19/admin-guide/cgroup-v2.html)
describes the shared quota and counters; those counters do not isolate this task.
These references explain measurement limits, not the cause of the prior failures.

Admission requires full native checks, exact same-image smoke and **three**
full-size 16-session / 512-solve operational pilots before the new source freeze.
Passing these pilots does not establish universal availability. The first policy
record contained a wrong ADR filename; a source-preserved second version corrects
that metadata before admission. No numerical or scientific record was changed.

The full uninstrumented native gate then records a 160.026 ms maximum sample gap,
145.680 ms maximum scan duration and 18 gap/scan events above 100 ms. These events
can overlap. Peak sampled RSS is 4.802 GiB against the 16 GiB stop; cleanup is empty.
This is direct evidence of delays admitted by the new rule, not an uninterrupted
sampling claim or a causal diagnosis of the earlier cohort.

## Observed resource behavior

Maximum sample-start gap: 240.818 ms; maximum scan duration: 220.665 ms; maximum guardian loop gap: 31.563 ms.
The coordinator records 227 gap/scan events above 100 ms. Their intervals may overlap and counts must not be added as elapsed time.
16 of 32 blocks contain such an event. Maximum heartbeat delivery lag is 13.814 ms. These distinct timing boundaries describe actual observations and do not identify the cause of a delayed scan.
Peak observed aggregate RSS is 2.914 GiB; this is a sampled observation, not a hard maximum.
All coarse environment snapshots and resource receipts remain visible without block exclusions.

## Validation and reproducibility

Full native gate: 638 repository Rust / 781 Python tests plus 28 isolated Rust tests, Clippy,
dependency audit, committed-record replay, artifact/documentation checks and smoke. The new
supervisor has 39 contracts. Same-image admission compares 64 smoke and 1536 full-pilot outputs
with the exact original scenarios. Existing device/four-sanitizer admissions are reused only for
the exact unchanged numerical source/image. Six analysis corruption guards reject changed work,
configuration, response bytes, original authority, cost partitions and duplicate cells; missing
sessions or resource failures suppress confirmation. Final acceptance additionally requires
all 512 complete sessions / 16384 certified solves.

The first full trajectory-verification reservation was undersized: the historical 10648-output
check took about 207 seconds, so a 240-second reserve did not provide adequate margin for
16384 outputs. It was stopped cleanly, its full 960 CPU seconds and source were retained,
and the same retained records were checked under a new 600-second CPU-only reservation.
This correction repeats verification, not scientific execution or timing.

[Analysis](data/mixed2-confirm2-analysis-v1.json), [block diagnosis](data/mixed2-confirm2-diagnosis-v1.json),
[portable response archive](data/mixed2-confirm2-records-v1.json).
Replay: `python3 tools/lp_mixed2_confirm2_analysis.py verify`.

The original independent serial checker covers 17984 response files / 58448 assessments / 144 distinct endpoint/tier pairs. Every trajectory, endpoint, audit, recovery, checkpoint and physical-work record matches admission. Portable replay passes without the original artifacts tree. All 2082 historical tracked files and prior handoff/backlog entries remain exact.

Independent allocation closed at 31824.747879588 / 96000 CPU and 5192.117661357 / 12000 GPU seconds, including 128 closing CPU seconds. Failed reservations: 1; all retain sources and full charges. Cleanup is empty; historical transfers are zero.
[Acceptance](data/mixed2-confirm2-acceptance-v1.json), [accounting](data/mixed2-confirm2-accounting-v1.json),
[development evidence](data/mixed2-confirm2-evidence-v1.json), [resource receipts](data/mixed2-confirm2-resources-v1.json.gz).

[Closing verification](data/mixed2-confirm2-closing-admin-v1.json).

GPUP-8 remains incomplete and GPUP-9 gated. Commit locally only.
