# Matched FP64 Control and GPU Study Overhead Repairs

Purpose: measure the ADR-0016 repairs and hand off an algorithmically matched
FP64 baseline. Owner: numerical backend and experiment tooling.
Status: completed development study, 2026-09-15; all 160 planned attempts retained.
Protocol: [ADR-0016](../decisions/ADR-0016-matched-fp64.md), with the unchanged
[GPUP-2 models and baseline](lp-baseline-gpup2.md).

## Findings

Matched CUDA certified **27/36 timing trials**, matching current host LP coverage;
reference and optimized legacy CUDA each certified **6/36**. On irregular-2048,
matched CUDA's certified median is **0.579 seconds**, versus **1.676 seconds** on
the host: a paired ratio of **2.896**, 95% bootstrap interval **[2.795, 3.359]**.
The GPU remains slower on smaller instances, where process/device startup dominates.
Three scheduling instances still fail original-model feasibility at the limits.

The repairs address distinct measured costs:

- Certification: reference and optimized legacy CUDA retain identical work and
  endpoint bits on all 33 mutually completed timing pairs. Irregular-2048's
  observed 50,000-step cost falls from 9.104 to 2.631 seconds. Both remain unclosed;
  this measures arithmetic overhead, not time to a certified solution.
- Control: optimized legacy uses 50,000 steps on irregular-2048 without closing;
  matched CUDA and host close at 1,400. All 27 mutually certified host/matched
  candidate, witness, objective, bound and gap values agree bit for bit.
- Harness: one schema snapshot replaces repeated schema construction, preserving
  document validation. All 160 jobs complete in one campaign invocation. Activity
  admission waits for quiet telemetry without assuming who caused recent activity.

Legacy cuda-lp retains its fixed anchors/weight. The new cuda-lp-matched uses the
unchanged host restart/weight algorithm and GPU kernels. No numerical target,
iteration reduction, certification frequency, solver default or baseline artifact
changed. These results select no lower-precision recipe.

## Frozen comparison and timing boundaries

Four configurations use three fresh-process repetitions on each of the same 12
development instances: reference e415918 CUDA, optimized legacy CUDA, matched CUDA,
and current host LP. Four separate profiles per configuration cover small-4,
irregular-256, irregular-2048 and dense_block-1024. Validation and held-out partitions
remain unmeasured. Pinned HiGHS 1.11.0 remains the fallback and was covered by
acceptance; no fallback occurred in these measurements.

The settings remain 50,000 iterations, checks every 200, published preconditioning
and restart/weight parameters, 1e-9 absolute/relative tolerances, one CPU thread,
solver seed 17, order seed 17001 and analysis seed 17002. Solve processes receive
10 seconds, followed by two seconds for cancellation/cleanup. GPU attempts reserve
16 seconds, including three seconds for leased activity admission and one second
for supervisor overhead. Host RSS and LP device-buffer limits remain 8 GiB each.
The device is RTX 5090 UUID GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48, driver
580.105.08, on an Intel Xeon Platinum 8457C host with CPU affinity [0].

Primary time runs from fresh child launch through independently assessed evidence,
serialization, exit and teardown. The additional standalone Rust verification is
outside this solve time and reported separately. Profiles add synchronized phase
boundaries; primary timing adds no synchronization solely for profiling. Activity
wait and lease queue wait are separate from solve time. All leased time is charged.

## Coverage and observed medians

Seconds; C = independently certified, W = completed at work limit without a
certified endpoint, T = censored timeout. Each entry summarizes three repetitions;
the classification is consistent across all three. A W/T median is observed process
cost, not a time-to-solution result. Timeout values include cancellation/teardown.

| Instance | Reference CUDA | Optimized legacy CUDA | Matched CUDA | Current host |
| --- | ---: | ---: | ---: | ---: |
| scheduling-20x5 | 2.914 W | 1.397 W | 0.744 C | 2.669 C |
| scheduling-50x10 | 10.225 T | 3.013 W | 3.329 W | 10.248 T |
| irregular-256 | 2.176 W | 1.349 W | 0.407 C | 0.186 C |
| irregular-2048 | 9.104 W | 2.631 W | 0.579 C | 1.676 C |
| dense_block-256 | 2.201 W | 1.396 W | 0.370 C | 0.195 C |
| dense_block-1024 | 5.382 W | 2.131 W | 0.472 C | 0.876 C |
| scaling-64 | 1.392 W | 1.206 W | 0.479 C | 0.123 C |
| scaling-256 | 2.122 W | 1.316 W | 0.487 C | 0.659 C |
| small-4 | 0.369 C | 0.369 C | 0.403 C | 0.007 C |
| small-16 | 0.376 C | 0.360 C | 0.356 C | 0.011 C |
| ta001-relaxation | 2.951 W | 1.365 W | 1.401 W | 9.736 W |
| ta011-relaxation | 3.498 W | 1.557 W | 1.559 W | 10.037 T |

Reference CUDA has 27 work-limit and three timeout outcomes; optimized legacy has
30 work-limit outcomes. Matched CUDA has nine work-limit outcomes; host has three
work-limit and six timeout outcomes. All remaining timing outcomes are certified.
No invalid/missing evidence, unsupported execution, device failure or fallback was
hidden or excluded from coverage. All 16 separate profiles also produced evidence.

### Paired certified host / matched CUDA ratios

A ratio above one favors CUDA. Compute median host time divided by median CUDA time
on the same repetitions. Resample paired repetitions 10,000 times with seed 17002;
report percentile 95% intervals. Three repetitions provide weak variability evidence
and discrete intervals, not cross-problem or cross-device generalization.

| Instance | Pairs | Ratio | 95% interval |
| --- | ---: | ---: | --- |
| scheduling-20x5 | 3 | 3.587 | [3.540, 4.238] |
| irregular-256 | 3 | 0.456 | [0.451, 0.484] |
| irregular-2048 | 3 | 2.896 | [2.795, 3.359] |
| dense_block-256 | 3 | 0.527 | [0.453, 0.539] |
| dense_block-1024 | 3 | 1.858 | [1.743, 1.870] |
| scaling-64 | 3 | 0.258 | [0.248, 0.308] |
| scaling-256 | 3 | 1.354 | [1.212, 1.366] |
| small-4 | 3 | 0.017 | [0.015, 0.021] |
| small-16 | 3 | 0.031 | [0.029, 0.032] |

There are no certified ratios for scheduling-50x10 or either Taillard relaxation.
Legacy/matched certified comparisons exist only for small-4 and small-16: ratios
0.916 [0.830, 1.062] and 1.010 [0.913, 1.149]. They mainly measure startup variability.
The full raw summary includes every comparison, including unavailable ratios.

### Certification isolation at identical completed work

These paired elapsed-cost ratios compare reference / optimized legacy CUDA. Except
for the two small certified instances, both endpoints are unclosed. Scheduling-50x10
is excluded because the reference times out. Endpoint bits and assessment indices
agree for all included pairs; iteration work is unchanged.

| Instance | Pairs | Cost ratio | 95% interval |
| --- | ---: | ---: | --- |
| scheduling-20x5 | 3 | 2.087 | [2.074, 2.166] |
| irregular-256 | 3 | 1.613 | [1.525, 1.668] |
| irregular-2048 | 3 | 3.460 | [3.385, 3.504] |
| dense_block-256 | 3 | 1.576 | [1.554, 1.617] |
| dense_block-1024 | 3 | 2.525 | [2.494, 2.525] |
| scaling-64 | 3 | 1.154 | [1.112, 1.202] |
| scaling-256 | 3 | 1.613 | [1.527, 1.629] |
| small-4 | 3 | 0.999 | [0.996, 1.195] |
| small-16 | 3 | 1.046 | [0.851, 1.149] |
| ta001-relaxation | 3 | 2.162 | [2.162, 2.279] |
| ta011-relaxation | 3 | 2.247 | [2.173, 2.465] |

The independent CPU component microbenchmark uses three blocks of 20 calls on
unchanged archived endpoints. The prior values come from the hashed
[diagnosis](lp-gpu-slowdown-diagnosis.md); this is a component comparison across
sessions, so the fresh-process paired comparison above is the stronger control.

| Instance | Prior certificate ms | Optimized certificate ms | Current model evaluation ms |
| --- | ---: | ---: | ---: |
| small-4 | 0.061246 | 0.000852 | 0.000818 |
| irregular-256 | 3.287251 | 0.241186 | 0.120645 |
| irregular-2048 | 26.454579 | 2.197723 | 1.220540 |
| dense_block-1024 | 13.644383 | 1.708121 | 0.886234 |

Only padding-only outward-enclosure work is pruned. Meaningful addition order,
1,024-element partitioning, signed-zero normalization, enclosure endpoints and
conservative refusals stay bit-identical to the retained literal padded oracle.
An 18-term sum now performs 17 meaningful enclosure additions rather than 1,023.
The independent exact-rational oracle remains the numerical regression authority.

## Separate phase profiles and remaining costs

Milliseconds, one separately synchronized profile per cell. Backend host checks
include candidate evaluation and certification. Final independent endpoint checks
are additional. Kernel time includes submission and synchronization, not just GPU
execution; host and device activity can overlap inside that phase.

| Instance / configuration | Steps | Restarts | Context | Backend checks | Kernel/sync | Controller | Independent endpoint | Full process |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small-4 / reference-cuda-lp | 200 | 0 | 326.634 | 0.171 | 3.187 | — | 0.103 | 431.326 |
| small-4 / cuda-lp | 200 | 0 | 260.708 | 0.019 | 3.145 | — | 0.035 | 355.726 |
| small-4 / cuda-lp-matched | 200 | 0 | 284.459 | 0.013 | 3.170 | 0.004 | 0.035 | 380.397 |
| small-4 / host-lp | 200 | 0 | — | 0.009 | — | — | 0.032 | 6.849 |
| irregular-256 / reference-cuda-lp | 50000 | 0 | 251.124 | 904.332 | 824.072 | — | 4.256 | 2106.870 |
| irregular-256 / cuda-lp | 50000 | 0 | 257.951 | 100.789 | 824.217 | — | 0.967 | 1294.624 |
| irregular-256 / cuda-lp-matched | 1200 | 5 | 240.683 | 2.948 | 19.794 | 1.521 | 0.949 | 359.009 |
| irregular-256 / host-lp | 1200 | 5 | — | 2.470 | — | — | 0.988 | 185.333 |
| irregular-2048 / reference-cuda-lp | 50000 | 0 | 360.172 | 7316.742 | 1234.406 | — | 35.463 | 9145.374 |
| irregular-2048 / cuda-lp | 50000 | 0 | 263.148 | 883.522 | 1234.289 | — | 9.530 | 2577.704 |
| irregular-2048 / cuda-lp-matched | 1400 | 6 | 357.305 | 29.550 | 34.594 | 14.336 | 9.008 | 649.215 |
| irregular-2048 / host-lp | 1400 | 6 | — | 26.656 | — | — | 10.196 | 1675.699 |
| dense_block-1024 / reference-cuda-lp | 50000 | 0 | 323.082 | 3815.347 | 1029.058 | — | 18.830 | 5347.413 |
| dense_block-1024 / cuda-lp | 50000 | 0 | 327.287 | 658.660 | 1029.604 | — | 6.184 | 2183.236 |
| dense_block-1024 / cuda-lp-matched | 1400 | 6 | 352.285 | 22.223 | 28.829 | 7.582 | 6.125 | 553.606 |
| dense_block-1024 / host-lp | 1400 | 6 | — | 19.658 | — | — | 6.095 | 875.005 |

A dash is inapplicable for host device phases; the host's KKT/controller work is
included in its iteration phase rather than separately available. Full raw profiles
also retain input preparation, preconditioning, invariant allocation/upload,
working allocation/upload, readback and solve-record serialization. These rows do
not partition all process time: launcher/runtime overhead, final evidence writing,
resource destruction and teardown remain in the residual. Fallback cost is
inapplicable in this study. Hardware bandwidth, occupancy and allocator-call
counters are unavailable; no resident-memory claim comes from virtual addresses.

On irregular-2048 the matched profile spends 357.305 ms in context setup, 26.489 ms
in preconditioning, 14.336 ms in controller work, 29.550 ms in backend checks and
34.594 ms in kernels/synchronization. Invariant allocation/upload is 0.800 ms;
working allocation/upload/readback together are 0.506 ms. The full process is
649.215 ms. Context/setup and the remaining process overhead now dominate this
case; transfers remain small. Repeated-solve throughput is outside this study.

Matched irregular-256 uses 1,200 steps, 7 backend assessments, 11 KKT evaluations,
5 restarts and 7,200 actual LP kernel launches. Irregular-2048 and dense_block-1024
each use 1,400 steps, 8 assessments, 13 KKT evaluations, 6 restarts and 8,400 launches.
Legacy uses 50,000 steps, 251 backend assessments and 300,000 launches on those
cases. The separately checked endpoint does not disappear from either path.

### Memory and certificate quality

Timing-run peak sampled RSS is 107.4–119.7 MiB for reference CUDA, 103.6–120.1 MiB
for optimized legacy, 108.1–119.9 MiB for matched CUDA and 0.6–26.9 MiB for host.
The largest recorded LP device-buffer peak is 1,627,768 bytes. The 10 ms process-tree
RSS watchdog can miss brief peaks and small short-lived host processes. LP buffer
counts exclude driver/context memory; CUDA virtual-address reservations are not RSS.
No 8 GiB watchdog or buffer limit was reached.

All certified results passed independent original-model feasibility and conservative
gap closure at the recorded tolerances. Host/matched certified evidence is bitwise
identical on these pairs; the largest absolute conservative gap is 8.448550943285227e-7
and the largest certificate allowance is 2.8312206268310547e-7. Relative tolerances
scale with objective magnitude; these are not a relaxed 1e-9 absolute target.
Certified endpoints required no dual-sign repairs. Both small legacy cases have
zero gap and zero certificate allowance.

Scheduling-50x10, ta001 and ta011 remain infeasible at 50,000 matched steps, so their
gap_upper is unavailable. Their conservative bounds are retained, but their
objective values do not establish feasible solutions. They use 17, 16 and 16
restarts respectively. GPUP-4 must retain these failures and numerical targets.

## Schema and activity accounting

Milliseconds, median of three fresh-snapshot-versus-reuse measurements against the
same current schema catalog. Every measurement still validates the whole document.

| Document | Fresh snapshot plus validation | Reused validator |
| --- | ---: | ---: |
| endpoint | 220.962 | 54.805 |
| ledger | 166.575 | 0.067 |

The snapshot checks each schema once and shares one reference registry; individual
large endpoint validation remains a real cost. Strict unknown-field, duplicate-key,
non-finite, identity, path and hash checks remain. Schema changes require a new
process; explicit fresh registries serve tests. Version-1 schemas/artifacts remain
unchanged and readable.

The single campaign invocation took 468.090 seconds. Pre-reservation activity waits
total 55.605846414 seconds and lease queue waits 0.002241305 seconds. No leased
activity race blocked an actual study job, and no campaign restart was needed.
Simulations cover activity decay, competing processes, unavailable/malformed
telemetry, cancellation and a post-lease race that launches no child. A persistent
leased race retains an attempted job, charges leased time and pauses the campaign.
It never silently retries. The coordinator and schema registry stay alive during
ordinary waiting. CPU solve processes total 112.098927740 seconds; additional
per-trial standalone verification totals 8.167883358 seconds.

## Budget and acceptance

The canonical original ledger carries forward 194.142866023 GPU seconds and charges
**251.845179881 additional seconds**, including profiles and all leased admission.
Cumulative consumption is **445.988045904 seconds**: 454.011954096 remain under the
900-second cumulative allowance; 1,354.011954096 remain in the baseline phase and
28,354.011954096 in the total campaign. The 600-second supplementary allowance,
1,800-second phase and 28,800-second total cap were respected. Other phase allocations
are unchanged. All 160 distinct jobs are settled; no crash reservation remains.

The full pinned-native gate passed before measurement with 405 Rust tests,
103 Python tests, dependency/license checks, committed artifact replay and
68 documentation pages (18.274 seconds). Four build jobs and all recorded CPU
gates/builds remained within the separate 60-minute CPU acceptance allocation.
Earlier prerequisite commits passed full native gates independently.

GPU acceptance ran sequentially under the shared lease: 38 regular device cases
(14 CUDA, 6 scheduling, 18 LP), plus two study-observation and three matched-control
cases under each of memcheck, racecheck, initcheck and synccheck. All passed with
zero errors; racecheck reported zero warnings. The first combined invocation then
caught a missing controller phase in endpoint-v2's schema. The schema/parser parity
fix gained a CPU regression and full native gate; affected CLI evidence, fallback
and replay checks passed a targeted leased rerun. Total acceptance consumption,
including that failed CLI attempt, is **79.673340271 leased seconds** of 1,800.
No kernel/controller code changed after the device suites. This is exact scoped
sanitizer coverage, not a claim that every historical test ran under every sanitizer.

Acceptance includes full 1,237-step host trajectories against the literal old loop,
check intervals 1/17/200 and nonzero controller-history gains; checkpoints across
checks/restarts and non-rollback deadlines/work; actual partial-device cancellation;
corrupted candidates/objectives/bounds/witnesses/status/control; both senses and
fallback; 138 padded-enclosure differential cases; exact-rational regressions;
schema/provenance tampering and archived preservation; crash/concurrent-resume,
phase/clock/lease/cleanup tests; and hand-checkable paired-analysis fixtures.
No required check remains unfinished. The three unclosed instances are retained
numerical outcomes, not waived acceptance failures. Final repository gate and local
commit evidence is recorded in [active task](../../state/active-task.md). The final
full pinned-native repository gate passed in 18.284103359 seconds with the same
405 Rust/103 Python tests and 69 documentation pages. Its raw log is retained in
artifacts/gpup3-final-acceptance/native.log, SHA-256
`8601cc1a629acab78d33c6661d7ddea10d00d35b7603f8d5be827f7832ec5f90`.

## Raw evidence and reproduction

Large outputs remain under ignored artifacts/gpup3-matched-fp64-v1. The index hashes
all raw trial, endpoint, worker, output, profile, component and acceptance evidence.
The summary contains full per-instance comparisons and unavailable measurements.
Measured current source is the archived dirty tree based on 223ee6c; later report
and task-state edits do not change that measured runtime. Reference source is the
immutable e415918 archive and its executable matches the frozen original baseline.

| Artifact | SHA-256 |
| --- | --- |
| campaign.json | `2fff49cff6f290f68324faeb49f1f1352ab6912c9db7f55b4fa8fab77627483e` |
| summary.json | `b9f034a00af8c97d314059728b9ca9b842c0e7cdd15e9ed78b872a76b8badb44` |
| artifact-index.json | `15038e92bf4115f947f971aa1c8305f499c4db4a43c4c145066bf3a902d0c0d6` |
| ledger.jsonl | `49ea15fc24a24fcabb4e677d6a684ea8a8d0d6c5fc1d1a52dba7b098c827a8f3` |
| execution.json | `2a288518e7586121e48aeebc656bf6da969f5f4cdec800e157ef8544076f0060` |
| source.tar | `f94a8f15fa3d2867aca8d9f9516879a6af686aea437ade0f013a05cddafdcafa` |
| cpu-components.json | `30216a871541fb443fcacd2948f13cf29b818f245b37b5acc591882e3cf50244` |
| comparison-audit.json | `ba5864c05713baca84c6dad9ab763c4fbb459c323efc0a863a504d473b1934b3` |
| fixed-work-ratios.json | `33fe825be73090a69969ea50c478350eba2ee5a8fcc1cce01db5551234aa7832` |
| Current binary | `3f145b255d0aae934eb88068f991ece09cc8a46c22b35c7970119ad736e91993` |
| Current code_object | `6a4c87550f7efec3ff2b29e247e604aac42d8cff83fa42f438d3823d15580f5e` |
| Current schema_snapshot | `6dfb48efda3c81c4178e13f54c40767d7b71e10e8320e176f5945f803e7e2fb3` |

Original baseline summary SHA-256 remains
`c57de898e75b5c422efd09ed3590e8e9d39f97f2b50ce99535f63d1c41a6cc63`;
its archived ledger remains
`aee3f1398725fedf8ad37d644c8960156b897b3a11478839359def4619eb8e37`.
The canonical budget ledger extends this history under the unchanged authority.
Reference executable SHA-256 is
`9538f9b16f1fdf3e224674a9c2e4f76f5e797022f730f858eaf63d2080b048fb`.

From the repository root, with pinned Rust/native prerequisites provisioned:

```bash
CARGO_BUILD_JOBS=4 bash tools/check.sh
cargo build --release -p optimizer-cli
cargo build --release -p optimizer-experiment --example lp_diagnose
python3 tools/benchmark_lp_matched.py --dry-run
python3 tools/report_lp_matched.py
```

The report command rechecks raw hashes, ledger history, settings, model provenance
and every endpoint with the Rust verifier. It performs no GPU solve. The component
measurement can be reproduced with `python3 tools/lp_matched_cost.py --output FRESH`.
The paired fixed-work supplement uses the same `tools/lp_report.py` paired_ratio
function on mutually completed reference/current repetitions; the bitwise audit
compares candidate values, duals, objective, bound, gap and assessment iteration.

`python3 tools/benchmark_lp_matched.py` resumes only unattempted jobs under the
original budget authority. Running it on this completed study adds no attempts.
A fresh comparative campaign requires a recorded identity and budget allocation;
copying a directory or removing a trial never authorizes repetitions. Reproducing
the reference build requires its pinned toolchain/native library and original build
path; a changed binary hash needs a newly recorded protocol. Device acceptance uses
`bash tools/gpu_job.sh GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 bash tools/lp_gpu_check.sh`.
See [study operations](lp-precision-study.md) for input preparation and limits.

## Handoff

GPUP-3 establishes the shared resumable FP64 control and measured overhead repairs.
GPUP-4 is ready to investigate measured startup/iteration overhead and bounded
residency/kernel improvements. Preserve legacy behavior, matched trajectories,
original-model authority, exact-rational tests, frozen data, failures and cumulative
spending. No lower precision, persistent checkpoint format, supported preset,
general comparative runner or publication is included.
