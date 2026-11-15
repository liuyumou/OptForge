# Exact checker and preparation optimization

SPEC-0042 / ADR-0075 continue the user's requested CPU optimization around the
admitted native/FP4 scenario executor. Public defaults, original-model authority,
GPUP-8 and GPUP-9 gates remain unchanged. The independently frozen confirmation follows CPU, native and device admission;
its final results and resource closure are recorded below.

## Implemented changes

The isolated `research/lp-mixed2-checker2` executor parses separate JSON constraint
objects concurrently and then calls the original model validator. It falls back
to the original parser on any error, preserving the original first error. It
retains exact binary64 parsing, the original input files and original-model hashing.

Dense column norm preparation visits contiguous rows, retaining the original
addition order within every column. The checker reduces separate lower, upper
and rounded arrays along the original 1024-leaf tree. A guarded normal-domain
TwoSum calculation produces the same directed result as the original arithmetic;
outside that domain, the original full-range reduction remains in use. Padding
additions and signed-zero behavior are retained. The final product path checks coefficient ranges once per immutable model and
repaired-dual ranges once per assessment. Operands with nonzero magnitudes in [2^-40,2^40]
produce normal products in [2^-80,2^80]; adjacent endpoints remain inside the
existing [2^-100,2^100] reduction guard. Exact integer significand multiplication
still decides whether a product needs outward rounding. Other magnitudes and
longer columns retain the original full-range path. There is no fast-math, changed
certificate tolerance or endpoint-answer cache.

The independent checker also reuses its existing original-byte SHA-256 for the
readiness message. This removes a redundant second hash of the same bytes, not
an input validation or identity check. Both native and FP4 use these changes.
The checker releases its transient original-byte buffer after constructing the
owned validated model and its hash; original input files remain retained.
The numerical solve body, device ownership, CUDA image, resets and policies are
unchanged.

## Diagnostic observations and rejected versions

Initial CPU attribution on coupled2048 measured about 438 ms of JSON parsing in
1007 ms of solver preparation and 32 ms of dual certification in a 43 ms checker
call. These are instrumented, local CPU observations, not complete-session gains.
Parallel parsing reduced the two-repeat median solver preparation from 1009 to
853 ms and checker preparation from 1078 to 908 ms. These small development
samples select work; they do not establish adoption.

A six-block uninstrumented CPU transport comparison assessed twelve identical
endpoints per cell with all versions and their outputs retained. Baseline versus
separate-field reduction medians (ms/call) were 16.979 → 15.348 for coupled1024,
60.092 → 55.862 for coupled2048, 16.834 → 15.190 for generic1024 and
60.615 → 54.824 for generic2048. These calls exclude model setup and are not
solver throughput results. The three-worker/fourth-control placement differs
from the initial four-worker CPU profile, so absolute timings across those
experiments must not be treated as an optimization effect.

A further exact product classifier cached significand widths to avoid most
128-bit multiplications. It passed full-domain numerical tests but was slower
than the selected tree implementation in all four repeated probe families
(15.781, 56.501, 15.777 and 56.806 ms). It is rejected; its sources, binary,
measurements and resource receipts remain retained. This is an observed timing
result, not evidence identifying an instruction/cache cause.

A later guarded-product probe reduced coupled1024 checker calls from about
9.751 to 5.618 ms and coupled2048 from 44.152 to 34.548 ms under the same wider
vector target. A bounded decimal-token parse cache passed exact tests but had
no consistent preparation benefit and regressed the 1024 preparation probe.
It is rejected and retained. The final parser uses the original validated
parallel parsing route; there is no coefficient-token or endpoint-answer cache.

One development build failed on an incorrectly escaped test literal before
compilation. Its source and full 960 CPU-second reservation remain retained.
The corrected build and final selected source pass. A separate memory-observation
launcher had an unmatched parenthesis before execution; its full 480 CPU-second
reservation and source are retained. Neither failure launched a scientific cell.

## Compiler-target diagnosis

A separate six-block comparison crosses baseline/candidate source with default
and `x86-64-v4` compilation on the admitted Xeon Platinum 8457C host. Strict
floating-point semantics remain enabled. Both builds pass their numerical tests;
all 1152 measured certificates match the retained original assessments exactly.
The selected candidate uses the wider-vector target, with public build defaults
unchanged. The comparison below separates compiler-target and source effects. This executable requires the recorded
host instruction capabilities; these performance results do not establish gains
on CPUs without them.


| Family | Baseline, default | Tree, default | Baseline, v4 | Tree, v4 |
|---|---:|---:|---:|---:|
| coupled-1024 | 17.063 | 15.222 | 14.956 | 9.716 |
| coupled-2048 | 59.526 | 52.885 | 56.545 | 43.988 |
| generic-1024 | 16.726 | 14.977 | 14.611 | 9.668 |
| generic-2048 | 59.057 | 53.930 | 56.291 | 43.955 |

Entries are median checker-call milliseconds from the six-block development
comparison, excluding model setup. Final guarded products and buffer release
were selected afterward; the complete-session candidate uses all selected changes.
All 2,880 exploratory comparison assessments match the original certificates.

The final idle-checker observation retains four independent validated models:

| Model size | Baseline RSS (MiB) | Candidate RSS (MiB) | Raw inputs (MiB) |
|---|---:|---:|---:|
| 1024 | 493.4 | 269.5 | 225.5 |
| 2048 | 1916.7 | 1019.2 | 899.8 |

These are instantaneous post-readiness RSS observations, not full-session peaks.
The near-input-size decrease is consistent with releasing the transient buffers.
Peak memory during parsing is still required; the sampled guard does not enclose
all sub-sample peaks.

## Prospective complete-cost comparison

Sixteen independently frozen paired blocks compare baseline and candidate in
four 1024/2048 generic/coupled families, both certification tiers and both lanes.
The 512 sessions each cycle four original scenarios eight times: 16384 solves.
Every fresh session includes original preparation, all model caches and switches,
independent checking, durable output, EOF and owned destruction. The comparison
uses exact simultaneous median intervals across 32 endpoints; scoped benefit
requires a ratio lower bound above one and saved time lower bound above 10 ms.
The provisional 1.10 comparison is reported separately. No failed/missing cell
is retried or pooled with historical studies.

Shared hardware, constructed repeated scenario streams, a limited family/size
range and temporal independence assumptions limit generalization. Sampled RSS
under the admitted one-second supervisor is not a hard memory enclosure. All
100 ms advisories remain visible without censoring performance observations.

## Independent confirmation results

Measurements use an Intel Xeon Platinum 8457C and the pinned NVIDIA RTX PRO 6000 Blackwell Server Edition (driver 580.105.08). The CPU instruction admission, GPU UUID and before/after block environment snapshots remain in the evidence.

All 16 planned blocks completed: **512 sessions / 16384 original-model certified solves**. Missing sessions: 0; partial responses: 0; failed blocks: 0. Every retained trajectory matches admission. No scientific retries or historical pooling were used.

Scoped benefit passes **16/16** implementation comparisons; **13/16** also pass the provisional 1.10 lower bound. These are candidate-versus-baseline comparisons within a solver lane. They do not constitute a public preset or a new FP4-versus-native adoption test.

| Family | Tier | Lane | Baseline → candidate (s) | Paired speedup [simultaneous interval] | Saved ms [interval] | Scoped / 1.10 |
|---|---|---|---:|---:|---:|---|
| coupled-1024 | 1e-7 | fp4x2 | 4.901 → 3.885 | 1.2692 [1.2128, 1.2969] | 1037.6 [846.5, 1119.2] | pass / pass |
| coupled-1024 | 1e-7 | native | 5.136 → 4.116 | 1.2437 [1.2178, 1.2554] | 1001.3 [913.4, 1048.7] | pass / pass |
| coupled-1024 | 1e-9 | fp4x2 | 5.799 → 4.538 | 1.2832 [1.2519, 1.2994] | 1281.9 [1155.1, 1332.2] | pass / pass |
| coupled-1024 | 1e-9 | native | 6.109 → 4.853 | 1.2580 [1.2300, 1.2753] | 1251.5 [1135.3, 1334.5] | pass / pass |
| coupled-2048 | 1e-7 | fp4x2 | 15.073 → 12.100 | 1.2501 [1.2218, 1.3665] | 3037.4 [2729.6, 4487.1] | pass / pass |
| coupled-2048 | 1e-7 | native | 15.678 → 12.726 | 1.2345 [1.2148, 1.2829] | 2978.3 [2750.9, 3494.5] | pass / pass |
| coupled-2048 | 1e-9 | fp4x2 | 17.853 → 14.049 | 1.2691 [1.2355, 1.2827] | 3775.6 [3360.8, 3971.6] | pass / pass |
| coupled-2048 | 1e-9 | native | 18.736 → 14.971 | 1.2486 [1.2228, 1.2780] | 3754.8 [3376.9, 4083.9] | pass / pass |
| generic-1024 | 1e-7 | fp4x2 | 2.923 → 2.527 | 1.1598 [1.1222, 1.2039] | 404.4 [313.7, 498.8] | pass / pass |
| generic-1024 | 1e-7 | native | 2.946 → 2.591 | 1.1348 [1.0987, 1.1883] | 349.7 [263.1, 485.5] | pass / unestablished |
| generic-1024 | 1e-9 | fp4x2 | 2.893 → 2.520 | 1.1507 [1.0816, 1.1964] | 383.5 [218.6, 483.6] | pass / unestablished |
| generic-1024 | 1e-9 | native | 2.937 → 2.575 | 1.1401 [1.0977, 1.1871] | 362.3 [258.3, 475.6] | pass / unestablished |
| generic-2048 | 1e-7 | fp4x2 | 9.429 → 8.128 | 1.1619 [1.1405, 1.2139] | 1305.3 [1186.6, 1686.5] | pass / pass |
| generic-2048 | 1e-7 | native | 9.586 → 8.156 | 1.1793 [1.1470, 1.3173] | 1457.1 [1236.6, 2634.9] | pass / pass |
| generic-2048 | 1e-9 | fp4x2 | 9.556 → 8.104 | 1.1818 [1.1301, 1.2217] | 1475.2 [1071.8, 1743.4] | pass / pass |
| generic-2048 | 1e-9 | native | 9.557 → 8.239 | 1.1570 [1.1223, 1.1963] | 1301.2 [1030.5, 1592.9] | pass / pass |

Across all 256 individual block pairs, 4 have candidate latency above baseline. The smallest observed ratio is 0.8313x (dense-generic-1024, certified-1e-7, fp4x2, block 5). Every such observation is retained; this is descriptive, not a separate tail-latency guarantee.

All 16,384 response cost/work records are independently bound to their session receipts; additive host partitions account for every elapsed nanosecond. Total physical work is 7372800 updates.

For the four unfavorable pairs, positive deltas mean the candidate took longer (milliseconds):

| Block | Family / tier / lane | Complete Δ | Setup Δ | Checker Δ | Other Δ |
|---|---|---:|---:|---:|---:|
| 5 | generic-1024 / 1e-7 / fp4x2 | 581.7 | -66.1 | 292.9 | 355.0 |
| 13 | coupled-1024 / 1e-9 / native | 221.6 | -55.9 | -166.4 | 443.9 |
| 0 | generic-2048 / 1e-9 / native | 232.9 | 998.9 | -724.0 | -42.1 |
| 10 | coupled-1024 / 1e-9 / fp4x2 | 121.0 | 1314.1 | -1154.1 | -39.0 |

The largest measured cost increase is located in audit for 1 pairs, checker for 1 pairs, setup for 2 pairs. These phase observations do not establish a scheduler, cache or device cause. Every pair remains in the frozen analysis.


Session columns are marginal medians; speedups and savings are medians of paired block values.
The interval uses the second and fifteenth ordered observations from sixteen independent blocks.
The exact per-endpoint coverage is 0.999481201; Bonferroni protects all 32 endpoints at familywise alpha 0.05. This discrete interval is conservative. Fifteen of sixteen blocks must exceed a threshold for its lower bound to exceed that threshold.
The prospective probability of passing the sign threshold is about 0.141, 0.515 and 0.811 when the per-block probability is 0.80, 0.90 and 0.95, respectively. Failure to pass 1.10 is not evidence of zero value.

## Complete cost and remaining work

| Family | Tier | Lane | Setup median, baseline → candidate (ms) | Checker median per session, baseline → candidate (ms) |
|---|---|---|---:|---:|
| coupled-1024 | 1e-7 | fp4x2 | 1724.5 → 1599.2 | 1772.8 → 925.7 |
| coupled-1024 | 1e-7 | native | 1654.7 → 1515.7 | 1774.7 → 930.7 |
| coupled-1024 | 1e-9 | fp4x2 | 1700.3 → 1628.6 | 2334.9 → 1181.7 |
| coupled-1024 | 1e-9 | native | 1600.4 → 1537.1 | 2333.9 → 1183.8 |
| coupled-2048 | 1e-7 | fp4x2 | 6197.2 → 5650.7 | 6115.5 → 3692.7 |
| coupled-2048 | 1e-7 | native | 6004.2 → 5489.6 | 6108.8 → 3695.0 |
| coupled-2048 | 1e-9 | fp4x2 | 6184.2 → 5613.8 | 8162.2 → 4935.2 |
| coupled-2048 | 1e-9 | native | 6059.9 → 5445.8 | 8137.8 → 4919.7 |
| generic-1024 | 1e-7 | fp4x2 | 1705.7 → 1578.7 | 588.8 → 308.8 |
| generic-1024 | 1e-7 | native | 1610.3 → 1546.7 | 588.4 → 309.6 |
| generic-1024 | 1e-9 | fp4x2 | 1680.8 → 1579.3 | 589.0 → 310.7 |
| generic-1024 | 1e-9 | native | 1601.2 → 1541.5 | 590.1 → 312.0 |
| generic-2048 | 1e-7 | fp4x2 | 6111.4 → 5655.4 | 2040.6 → 1245.9 |
| generic-2048 | 1e-7 | native | 6017.4 → 5454.2 | 2043.8 → 1241.1 |
| generic-2048 | 1e-9 | fp4x2 | 6243.2 → 5640.3 | 2054.3 → 1241.6 |
| generic-2048 | 1e-9 | native | 6008.1 → 5537.8 | 2023.8 → 1240.8 |

For strict coupled2048 FP4, complete-session medians change from 17.853 to 14.049 seconds, with the same 800 updates per solve. The candidate's aggregate complete cost comprises 40.5% setup and 34.8% independent checking. GPU events average 37.358 → 37.346 ms/request; the CUDA image and numerical work are unchanged.

All cost partitions, per-block values and order strata are retained in the machine-readable analysis.
GPU events are nested within host iteration time and must not be added again to host partitions.
Setup includes fresh original-model preparation, checker startup, all four cached models and lane preparation.
The remaining outer cost includes switching, transport, durable outputs, teardown and measurement bookkeeping.
Session-receipt publication and post-session verification occur after the measured session and are charged to the study allocation.
Aggregate cost shares use sums; the report does not add marginal medians as if they were one observed session.

Further preparation and exact-assessment work may still reduce complete cost. These partitions identify measured targets,
not a demonstrated next optimization. No follow-on study or allocation is released.

## Order sensitivity and limits

| Family | Tier | Lane | Baseline first | Candidate first |
|---|---|---|---:|---:|
| coupled-1024 | 1e-7 | fp4x2 | 1.2710 | 1.2598 |
| coupled-1024 | 1e-7 | native | 1.2498 | 1.2373 |
| coupled-1024 | 1e-9 | fp4x2 | 1.2844 | 1.2767 |
| coupled-1024 | 1e-9 | native | 1.2603 | 1.2563 |
| coupled-2048 | 1e-7 | fp4x2 | 1.2407 | 1.2567 |
| coupled-2048 | 1e-7 | native | 1.2399 | 1.2331 |
| coupled-2048 | 1e-9 | fp4x2 | 1.2695 | 1.2691 |
| coupled-2048 | 1e-9 | native | 1.2423 | 1.2586 |
| generic-1024 | 1e-7 | fp4x2 | 1.1691 | 1.1461 |
| generic-1024 | 1e-7 | native | 1.1689 | 1.1255 |
| generic-1024 | 1e-9 | fp4x2 | 1.1705 | 1.1377 |
| generic-1024 | 1e-9 | native | 1.1423 | 1.1103 |
| generic-2048 | 1e-7 | fp4x2 | 1.1619 | 1.1630 |
| generic-2048 | 1e-7 | native | 1.1751 | 1.1870 |
| generic-2048 | 1e-9 | fp4x2 | 1.1950 | 1.1683 |
| generic-2048 | 1e-9 | native | 1.1411 | 1.1711 |

Each order stratum has eight paired blocks; no finite simultaneous interval is available at the frozen alpha.
These medians are descriptive sensitivity observations, not separate passing tests or grounds for excluding blocks.
FP4/native within-block ratios are also retained as descriptive contrasts; the primary inference compares implementations within each lane.
The control is the original admitted portable executable; the selected candidate combines source improvements and the host-specific v4 target.
The factorial CPU experiment uses the earlier tree candidate; the final guarded product path was selected afterward.
It separates source/target influences for that checker version, but is not a final-candidate or full-session factorial confirmation.
Constructed cyclic scenarios, the shared CPU/device and possible temporal dependence limit production and cross-host claims.

A retained four-request smoke session had 4907.304 ms of candidate setup versus 1641.481 ms for its paired baseline
(generic1024 / 1e-7 / FP4). It passed numerical and resource admission. Its cause is unassigned; it was not censored or used to tune the frozen cohort.

## Supervision and acceptance

The unchanged one-second supervisor completed every block. Maximum observed sample-start gap was 190.202 ms; maximum scan work was 180.480 ms. All 133 gap/scan observations above the 100 ms advisory remain in the receipts; overlapping gap and scan observations are not independent events. Peak aggregate sampled RSS was 2.921 GiB. This is sampled memory, not a hard enclosure. Cleanup is empty.

Final implementation acceptance passes 638 repository Rust tests, 785 Python tests and 31 isolated Rust tests, plus format, Clippy, dependency, replay, artifact, documentation and smoke checks.
All 20 model preparations match full serialized original inspection hashes. CPU admission includes 204 original certificate assessments and 2304 rational product outputs.
Fresh device acceptance covers 130 arithmetic/lifecycle cases, 22 process/configuration cases, seven invalid switching cases and four recovery comparisons.
The original four complete sanitizers and four scenario-switch sanitizer suites are reused only for the exact unchanged CUDA image, ownership code and solve body; their source-bound receipts are retained.
Final smoke and full-size pilot add 1152 exact trajectory comparisons. The original serial checker independently rechecks every distinct final/audit endpoint and tier.
Deduplication is only a verification technique; runtime certificates are computed independently on every request.

Independent serial verification covers **17536 response files / 56992 assessments / 144 distinct endpoint/tier pairs**.

The two early failed development reservations retain all sources and the full 1440 CPU seconds. Portable replay setup later failed before verification because /tmp and the workspace are different filesystems and hardlinks cannot cross that boundary. Its full 3600 CPU-second reservation is retained. A same-filesystem temporary checkout uses the unchanged frozen reader with no artifacts directory inside that checkout. All three failures total 5040 CPU seconds; none was a scientific retry. A dependent device launcher was also cancelled before reservation, with its record retained.

The portable archive preserves every original scientific response byte, model input, source snapshot, failed version and settled receipt.
It verifies exact numerical trajectories, executable/image bindings, coverage, lifecycle partitions and all statistical decisions without the original artifacts tree.
Executables and disposable build caches remain local; their immutable digests and source are retained. Publishing omits its own unfinished administrative receipts; settled closing receipts and later sources are preserved in the separate resource archive.


## Descriptive FP4/native contrast

Ratios below are native complete-session time divided by FP4 complete-session time within each block.
These comparisons are descriptive, with no separate significance or adoption claim; they do not regrade the earlier MIXED2 confirmation.

| Family | Tier | Original executor | Optimized executor |
|---|---|---:|---:|
| coupled-1024 | 1e-7 | 1.0479 | 1.0633 |
| coupled-1024 | 1e-9 | 1.0571 | 1.0729 |
| coupled-2048 | 1e-7 | 1.0358 | 1.0513 |
| coupled-2048 | 1e-9 | 1.0509 | 1.0594 |
| generic-1024 | 1e-7 | 1.0127 | 1.0298 |
| generic-1024 | 1e-9 | 1.0085 | 1.0201 |
| generic-2048 | 1e-7 | 1.0168 | 1.0151 |
| generic-2048 | 1e-9 | 0.9989 | 1.0219 |

## Reproduction and closure

From a checkout containing the evidence parts, run `python tools/lp_checker2_evidence.py portable` to verify every archived byte and reproduce the frozen decisions without CUDA, executables or the original artifacts tree.
The measured binary can be rebuilt from the retained source/toolchain and recorded compiler flags; its device use still requires the normal admission and resource contract.

[Cost and unfavorable-pair diagnosis](data/checker2-diagnosis-v1.json).
[Complete analysis](data/checker2-analysis-v1.json).
[Portable evidence index](data/checker2-evidence-v1.json).
[Acceptance](data/checker2-acceptance-v1.json).
[Historical preservation](data/checker2-history-v1.json).
[Accounting](data/checker2-accounting-v1.json).

Independent allocation closed at **44892.726186584 / 96000 CPU seconds** and **5807.763245136 / 12000 GPU seconds**, including 512 preparation and 128 closing CPU seconds. All 3 failed reservations retain full charges. No historical allocation transfer; cleanup is empty. Public defaults, GPUP-8 incomplete and GPUP-9 gated remain unchanged.
