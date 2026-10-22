# Bounded host-assessment scheduling: GPUP-ASSESS

Status: implemented and evaluated under accepted ADR-0039; no supported preset.
Owner: numerical backend and experiment tooling
Introduced: 2026-10-22
Last reviewed commit: bootstrap

[ADR-0039](../decisions/ADR-0039-bounded-assessment-scheduling.md) accepts the
bounded assessment subset of [SPEC-0021](../specifications/SPEC-0021-lp-refinement.md).
This experiment compares fixed_200 with bounded_800 on tuned FP64 and existing
accumulation FP32. Every numerical restart/weight check remains at 200 updates;
only optional original-model assessments are scheduled. Original-model host
validation, outward certification and conservative gap remain authoritative.

The frozen study retains **60/60 attempts**, independently verifies **57 endpoints**
and certifies **24/48 primary timings**. FP64's irregular-32768 paired speedup is
**1.0272x** (three repetitions; bootstrap 95% interval 1.0190–1.0342). Certified
coverage is unchanged, smaller cases provide no clear benefit, and fixed FP32
still fails on larger models. No supported preset is selected.

## Policy and endpoint

At each controller boundary, bounded_800 measures maximum normalized movement
of scaled primal/dual coordinates since the preceding sample. It requests full
assessment at the first boundary, after a factor-two movement decrease relative
to the last assessed sample, for invalid indicators, or after 800 updates.
Zero movement is only a scheduling signal. Every safe final endpoint receives
fresh original-model assessment, including partial final intervals. Cancellation,
deadline and numerical/device failure retain their termination reason.

A certifiable point can disappear before the next selected assessment. The
maximum spacing therefore provides no bound on missed transient success.
Diagnostic trajectories continue past successful points, with no successful
primary timing claim. Independent replay counts saved assessments, delayed
success, missed transient success and censored horizons, including the mandatory
final assessment. Failed work and all physical updates remain charged.

## CPU admission

The [reviewed receipt](data/assess/cpu-admission.json) retains 16 common
trajectories: both arithmetic modes on all eight GPUP-EXEC models, 4000 updates
each. Independent original-model checks cover all 320 boundary witnesses.
The original frozen CPU source/executable, raw frames, stdout/stderr and original
receipt remain under artifacts/gpup-assess-v1/admission. A separate CPU-only
review includes the final mandatory assessment in discovery accounting; no
trajectory is rerun or replaced. Synthetic transient-success, delayed-success,
zero/subnormal-motion and extreme finite-range tests remain explicit.

The CPU source receipt also preserves and corrects the generic reader's debug
label for the actual frozen release/examples executable. This label never denotes
a GPU execution or a measured solver speedup.

The trajectories use 545.510899 CPU seconds, 559.531507197 elapsed seconds and
493043712 bytes maximum child RSS. CPU evidence establishes policy semantics and
common-trajectory behavior; it is not measured GPU latency or convergence evidence.

## Frozen online protocol

The [protocol](../../benchmarks/configs/lp-assess-v1.json) freezes 48 fresh timings:
four configurations, three repetitions and small-4/irregular-2048/irregular-32768/
mixed-65536. Twelve separate 2000-update profiles cover irregular-2048,
irregular-32768 and mixed-65536 with complete intermediate witness attachments.
Preserve seed 17, order seed 17001, analysis seed 17002, 1e-9 tolerances,
50000-update primary limits and inherited 10/30-second deadlines.

The fresh-process endpoint includes host parsing/preparation, context creation,
residency, updates, every controller check, movement, host assessments, final
certification, witness output and teardown. Independent post-run verification is
outside primary latency. `solve_loop` includes original-model assessments;
`original_model_assessments` is a nested subset and must not be added to it.
CUDA images and arithmetic are unchanged. No device busy-time or hardware-counter
claim follows from host-observed phase durations.

All work uses the selected 5090 UUID GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48,
selected-device activity admission and the shared host lease. Task allocation is
2300 GPU seconds: timing 1300, profiles 450, acceptance 550. Worst-case frozen
reservations are 1248/432/516 seconds. The prior 16684-event ledger prefix and
19207.265220123 / 21602.574545061 cumulative charge remain exact. No primary
identity can retry; refusals, failed endpoints and missing endpoints remain visible.

## Certified latency and coverage

Seconds below are medians of certified fresh-process samples; parentheses give
certified/planned repetitions. An unavailable cell has no certified latency.

| Arithmetic / schedule | small-4 | irregular-2048 | irregular-32768 | mixed-65536 |
| --- | --- | --- | --- | --- |
| Tuned FP64 fixed_200 | 0.2975 (3/3) | 0.4097 (3/3) | 2.1198 (3/3) | unavailable (0/3) |
| Tuned FP64 bounded_800 | 0.3522 (3/3) | 0.4059 (3/3) | 2.0636 (3/3) | unavailable (0/3) |
| Accumulation FP32 fixed_200 | 0.3009 (3/3) | unavailable (0/3) | unavailable (0/3) | unavailable (0/3) |
| Accumulation FP32 bounded_800 | 0.3619 (3/3) | unavailable (0/3) | unavailable (0/3) | unavailable (0/3) |

The independently verified [summary](data/assess/summary.json) and
[all trial outcomes](data/assess/trials.csv) retain failures and uncertainty.
Ratios use the median of paired fixed/bounded latencies, with 10000 bootstrap
resamples and seed 17002; they are not ratios of the cell medians. FP64 ratios
are 0.8448x on small-4 (0.8380–1.1530), 0.9839x on irregular-2048
(0.9715–1.0448), and 1.0272x on irregular-32768 (1.0190–1.0342).
Small-4 saves no assessments; its interval crosses one. Three development
repetitions do not establish a general recipe or independent held-out benefit.

All 45 complete timing endpoints verify. Nine timings retain their FP32 numerical
failure on each policy: physical updates are 47000 on irregular-2048, 40464 on
irregular-32768 and 20400 on mixed-65536. Bounded scheduling reduces assessments
235→62, 203→53 and 102→28 respectively, with identical failure endpoints.
These are unsuccessful solves, never certified speedups. The three fixed-FP64
mixed timings time out without endpoints; the bounded counterparts reach the
50000-update limit with a verified endpoint but no certificate. Every interruption
and missing endpoint remains visible, without retries.

## Common-trajectory profiles

All twelve separate 2000-update profiles verify. All six policy pairs have
bitwise-identical intermediate frames and final numerical/work state. Assessments
include the mandatory final check; every numerical controller check remains.

| Model / arithmetic | Fixed assessments | Bounded assessments | First certifiable / detected update |
| --- | ---: | ---: | --- |
| irregular-2048 FP64 | 11 | 9 | 1400 / 1400 |
| irregular-2048 FP32 | 11 | 6 | none within horizon |
| irregular-32768 FP64 | 11 | 9 | 1400 / 1400 |
| irregular-32768 FP32 | 11 | 5 | none within horizon |
| mixed-65536 FP64 | 11 | 10 | none within horizon |
| mixed-65536 FP32 | 11 | 5 | none within horizon |

No delayed or missed successful point is observed in these six profiles or the
16 CPU traces. Unsuccessful horizons remain censored, and synthetic fixtures
retain a missed transient success and a 600-update detection delay. The CPU
replay skips 204 of 320 boundary assessments. None of these diagnostic counts
substitutes for certified fresh latency.

## Acceptance, review and resources

Full pinned-native tools/check.sh passes before the frozen cohort. All 66 ordinary
device tests, three assessment-specific tests, six 2000-update policy pairs and
twelve same-device replays pass. Memcheck, racecheck, initcheck and synccheck each
pass the scoped assessment smoke case with zero reported errors/hazards. Device
acceptance remains bound to the measured source/executable and unchanged CUDA
images; subsequent CPU review is recorded separately below.

CPU-only final review strengthens signed-zero replay comparison and prevents
unverified/partial profiles from entering trajectory comparisons. The old
float-value comparison accepts +0.0 and -0.0 as equal; the reviewed comparison
preserves their bits. All twelve retained GPU replays already match bitwise.
The rebuilt host verifier accepts all 57 available study endpoints. Exact
[source bridges](data/assess/review-source.json) preserve five before/after files,
the complete original report, numerical modules, host authority and solve/output
bodies. The [review receipt](data/assess/host-review.json) adds no GPU execution or
allowance, and the reviewed report has identical numerical results and charges.
Device acceptance/timings remain bound to their original frozen executable;
reviewed-source acceptance is a separate CPU gate.

PR review reproduces and repairs cross-session checkpoint restoration, which
could import logical state with a new work allowance and deadline. Snapshots now
belong to the originating session. It also rejects inconsistent failure metadata
and oversized controller counters, and prevents an interrupted profile from
borrowing success discovery from the other policy's longer horizon. Incomplete
profile outcomes remain in the trial rows with unavailable pair comparisons.
All retained profiles complete their horizons, so results and charges are
unchanged. The [PR source bridge](data/assess/pr-review-source.json) preserves the
prior bridge, exact before/after sources and unchanged execution-loop, original
host authority and solve/output bodies. These are CPU-only repairs with no new
device acceptance or timing claim for the revised executable.

The [PR pinned-native gate](data/assess/pr-native-acceptance.json) passes all 323
Python tests, Rust/native/dependency checks, historical replay, 132 documentation
pages and smoke. It uses 128.427299756 elapsed / 180.294952 CPU seconds and
1658880000 bytes sampled process-tree RSS. Native coverage is enabled and GPU
work is zero. Every one of the 1468 frozen artifact files remains byte-identical.

A final reader regression intercepts the previous default, which would replace
the earlier CPU-review report. The PR reader now defaults to its separate
`artifacts/gpup-assess-pr-review-20261022/report-final.json` and rejects either
historical report path, including aliases. A separate
[final source bridge](data/assess/pr-review-final-source.json) retains both PR
source cohorts, tools and diffs. Both historical reports remain immutable.

The [final PR pinned-native gate](data/assess/pr-final-native-acceptance.json)
passes all 324 Python tests plus Rust/native, dependency, historical replay,
documentation and smoke checks in 116.991061611 elapsed / 144.139803 CPU seconds,
with 1663926272 bytes sampled process-tree RSS. The rebuilt host verifier accepts
all 97 retained study/acceptance/replay/CPU-trace endpoints, including the 57 study
endpoints, in 1669.733762 CPU seconds and 512024576 bytes sampled process-tree RSS.
No GPU execution is added; both earlier review gates and their exact sources
remain separate evidence.

| Charge | Used GPU seconds | Task cap |
| --- | ---: | ---: |
| Timing / screening | 413.636131592 | 1300 |
| Profiles / ablations | 32.633232920 | 450 |
| Acceptance / repeatability | 77.405228209 | 550 |
| Total | 523.674592721 | 2300 |

Cumulative consumption is **19730.939812844 / 21602.574545061 GPU seconds**.
The **16816-event** ledger SHA-256 is
`dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c`, preserving the
exact 16684-event prefix
`e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535` and every earlier
prefix and phase ceiling. No allowance was added and no headroom is reserved.
Task artifacts remain under artifacts/gpup-assess-v1; final native CPU resources
and the checksum inventory are retained there. All admission/model/host/device/
artifact limits hold; the largest sampled timing/profile process RSS is
364781568 bytes, below the 8 GiB host cap.

## Reproduction and acceptance

```sh
python3 tools/lp_assess_admission.py --output artifacts/gpup-assess-reproduction/admission
python3 tools/benchmark_lp_assess.py --dry-run
python3 tools/report_lp_assess.py
```

CPU trace/replay and host verification need no driver or device. The study-only
`lp_precision_assess solve|verify|replay|trace-cpu|replay-trace MODEL REQUEST EVIDENCE`
example uses strict lp-assess-v1 documents. Evidence binds model/settings,
source/executable/images, device, work and each trace attachment. Scheduler and
controller checkpoints restore together without refunding work or deadlines.
Ordinary selectors, defaults, historical evidence and required adaptive audits
retain their meaning. Sessions, refinement combinations, promotion/recovery and
supported presets are outside this slice.

The earlier [reviewed-source pinned-native acceptance](data/assess/native-acceptance.json)
passes 322 Python tests, Rust/native/dependency checks, historical replay,
132 documentation pages and smoke. It uses 123.223139896 elapsed / 163.805355 CPU
seconds, 1662132224 bytes sampled process-tree RSS and 1663143936 bytes maximum
child RSS, with native coverage enabled and zero GPU work. Local delivery completes
this slice. GPUP-7 is the next contract task and requires its own numerical/resource
acceptance. No assessment/adaptive/refinement combination or preset is implied.
