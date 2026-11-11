# GPUP-RESIDENT2: native resident execution and complete delivery costs

Status: bounded implementation and comparison complete, 2026-11-11; performance retention gate fails.

Decision: keep the matched tuned native control. The resident candidate preserves certified coverage and reduces synchronization, but does not establish the required complete-delivery improvement. Its cold model-median geometric mean is **1.027370x**; four of seven certified model medians are below 1.0. No supported preset or faster-arithmetic claim follows.

Contract: [SPEC-0024](../specifications/SPEC-0024-native-resident-execution.md) and [ADR-0053](../decisions/ADR-0053-native-resident-execution.md). [Machine results](data/resident2-result-v1.json), [frozen manifest](data/resident2-manifest-v4.json), [delivery audit](data/resident2-acceptance-v1.json), and [source bridge](data/resident2/prerequisite-source-bridge.json).

## Implementation and endpoints

The feature-gated [runtime](../../crates/optimizer-lp-cuda/src/resident2.rs) adds immutable prepared models and a separate resident session. Cold workers include model parsing, preparation, context creation and import. Prepared batches reuse the same immutable model/residency for three fresh projected-zero solves; every solve has a fresh controller, working buffers and independent original-model certificate.

The candidate precomputes at most 200 exact native FP64 coefficient pairs. One buffer carries their binary64 bits and disjoint u64 sticky flags. Warp32 fused kernels retain the original arithmetic order, predicate failed coordinates, and submit no more than 200 updates before observation. Host adoption is transactional: read both vectors and all flags into scratch, reject a flagged/nonfinite window, preserve the complete host checkpoint and charge attempted work. Cancellation is polled every 64 submissions and after readback; required host control checks remain every 200 updates.

The [driver](../../crates/optimizer-lp-cuda/examples/lp_resident2.rs) exports actual original-unit vectors on normal limits. The active coordinator is [study v4](../../tools/lp_resident2_study_v4.py); v1–v3 and all failed acceptance artifacts remain immutable. Existing backends, numerical bodies, public defaults and the strict 1e-9 checker are unchanged.

## Frozen comparison

Eight development models, two modes, three paired cold repetitions and one prepared batch of three per mode/model produce **64 completed cells and 96 endpoints**. No cell was retried or omitted. Each mode certifies **42/48 endpoints**; all 42 certified control/resident pairs have identical candidate bytes and iteration counts. The remaining twelve mixed-model endpoints are delivered and uncertified.

All jobs use the RTX PRO 6000 UUID pinned in the manifest, four CPU slots, one shared GPU lease, 50000 update allowance and an eight-second native deadline. Cold cells reserve 60 wall seconds and prepared cells 100, including the independent checker. Native limits remain limits. Parent elapsed includes process startup/teardown, durable worker output and independent checker delivery; the final parent receipt write is excluded. Native host-cost instrumentation is enabled identically in both modes and adds no device synchronizations. Nested native costs are subsets, never added again to phase totals.

Ratios are control/resident: above one favors resident. The paired median is not the ratio of the two marginal medians shown in the table. The range is the three observed paired ratios, not a confidence interval. Three repetitions do not establish a general performance ranking. Prepared throughput has one batch per mode/model and no independent repetition uncertainty.

| Model | Control cold median (s) | Resident cold median (s) | Median paired ratio | Observed ratio range | Strict endpoints per mode |
| --- | ---: | ---: | ---: | --- | ---: |
| small-4 | 0.555764 | 0.609660 | 1.208557 | 0.7471–1.3256 | 6/6 |
| irregular-2048 | 0.583242 | 0.600586 | 0.991178 | 0.9626–0.9995 | 6/6 |
| dense_block-1024 | 0.522451 | 0.524402 | 0.996279 | 0.9623–1.0267 | 6/6 |
| scaling-256 | 0.467264 | 0.470600 | 0.984437 | 0.9747–1.0049 | 6/6 |
| scheduling-20x5 | 0.580539 | 0.563149 | 1.030675 | 1.0019–1.0384 | 6/6 |
| irregular-32768 | 3.873634 | 3.851801 | 1.005668 | 0.9802–1.0289 | 6/6 |
| dense_block-65536 | 9.780551 | 9.878888 | 0.992031 | 0.9577–1.0116 | 6/6 |
| mixed-65536 | 14.181380 | 14.166621 | ineligible | — | 0/6 |

The predeclared retention rule requires no coverage loss, improvement in every fully certified cold model median, a geometric mean of at least 1.05, and useful work. Coverage is preserved; the latency conditions fail. Mixed-model durations above are delivery observations, not certified speedups.

## Where complete time goes

Dense-65536 illustrates the remaining host/evidence cost. These are separate phase medians (their sum need not equal the median of the total); each individual row has an exact disjoint partition including an unattributed residual.

| Phase | Control median (s) | Resident median (s) |
| --- | ---: | ---: |
| conversion | 1.114595 | 1.092969 |
| preparation | 1.212486 | 1.173918 |
| import | 0.381975 | 0.389258 |
| native | 2.396819 | 2.363361 |
| export | 0.012638 | 0.012729 |
| check | 3.159025 | 3.153996 |
| output | 0.003652 | 0.003969 |
| unattributed | 1.495861 | 1.706111 |

The residual includes process startup/teardown, provenance hashing and metadata work. It is reported, not assigned to arithmetic. In the nontrivial admission trace both modes submit 2800 kernels for 1400 updates. Control/resident synchronize 58/44 times; upload bytes rise from 262144 to 513920 and readback bytes from 229376 to 481152. Fewer waits alone do not guarantee lower total cost.

| Model | Control prepared seconds/solve | Resident prepared seconds/solve | Control cold / prepared | Resident cold / prepared |
| --- | ---: | ---: | ---: | ---: |
| small-4 | 0.186258 | 0.264021 | 2.9838 | 2.3091 |
| irregular-2048 | 0.324377 | 0.325319 | 1.7980 | 1.8461 |
| dense_block-1024 | 0.267224 | 0.268876 | 1.9551 | 1.9504 |
| scaling-256 | 0.231804 | 0.238967 | 2.0158 | 1.9693 |
| scheduling-20x5 | 0.342359 | 0.342805 | 1.6957 | 1.6428 |
| irregular-32768 | 2.942805 | 3.033453 | 1.3163 | 1.2698 |
| dense_block-65536 | 7.867751 | 7.951015 | 1.2431 | 1.2425 |
| mixed-65536 | 12.559683 | 12.684230 | 1.1291 | 1.1169 |

Prepared numbers amortize setup and are throughput observations, not single-solve speedups. Mixed-model throughput remains uncertified.

## Normal limits and bound authority

All twelve mixed-65536 endpoints export 65536 primal and 65536 dual entries. They remain native limits with no strict certificate. The independent checker refuses a finite contribution for variable 3 because its reduced-cost enclosure requires an infinite variable-bound side. Primal feasibility does not supply a finite dual bound, and this refusal does not prove the model unbounded. No bound clipping, artificial finite bound, tolerance relaxation or optimizer-based repair is introduced.

## Acceptance, failures and accounting

The full native CPU integration gate passes 638 Rust tests, 515 Python tests, pinned HiGHS build, Clippy/format, workspace build/docs, dependency policy, artifact checks, committed-record replay, 190 documentation pages and CPU smoke. New focused coverage includes two CPU coefficient/preparation tests and five Python timing/counter tests. The test-only overflow correction has scoped lint/CPU validation and an exact production-source bridge.

Device acceptance covers bitwise window endpoints at 1/63/64/65/199/200 updates, 2000-update restart/controller trajectories, repeated prepared solves, cancellation, sticky overflow refusal and whole-window host preservation. Four nontrivial endpoint exports certify independently and match bitwise. Memcheck, racecheck, initcheck and synccheck each pass with zero errors/hazards.

Retained failures: initial enum-name compilation failure; an example compilation failure masked by a shell lacking `set -e` (the missing full reservation is separately charged); the first full CPU gate refusing stale historical source rosters; a nonoverflowing overflow fixture; and a correction attempt bound to the stale test executable. No arithmetic failure is inferred from those fixture/build errors. The original records, binaries and charges remain. The artifact reader was corrected before timing because the legacy diagnostics deliberately omit execution counters; actual disjoint native-cost scopes supply the counts without a device rerun.

The new envelope is 32000 CPU / 1800 GPU seconds, independent of historical ledgers. GPU charge is **598.631222067 seconds**: acceptance 247.592544461 (including both full failed 60-second reservations), study 351.038677606. The delivery audit conservatively includes its own full finalization reservation. The final closed CPU totals and cleanup are recorded separately in `docs/benchmarks/data/resident2-final-accounting-v1.json`; all earlier reservations and evidence checks are in the audit. Host memory is sampled under the unchanged in-container supervisor; this is not hard cgroup containment. Device allocations are admitted against 12 GiB.

The six changes to pre-existing source files are additive module/example/atomic-guard registration and test-only historical fixture adaptation. All other prior source hashes and all prior scientific results/charges remain exact. No vendor binary, credential or experiment directory is committed.

## Handoff

GPUP-RESIDENT2 is complete as a bounded negative optimization result with working lifecycle/phase instrumentation and normal-limit export. Keep the native control for subsequent comparisons. GPUP-MIXED2 is the next contract/implementation slice; this delivery reserves no work for it. GPUP-8 remains incomplete and GPUP-9 remains gated.
