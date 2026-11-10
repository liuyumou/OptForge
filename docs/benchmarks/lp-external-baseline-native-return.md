# GPUP-BASELINE completion under the native-return policy

Date: 2026-11-10. Status: complete screening roster under the user's
[native-return amendment](../decisions/ADR-0052-baseline-native-return.md).
All **240/240 planned cells** have settled attempts; **198**
meet their declared comparison policy and **135** meet the unchanged
independent certificate policy. These are distinct outcomes. No result is
certified merely because its solver returned normally.

The [machine report](data/external-baseline-native-result-v1.json) includes every
row, native error/status, original-model diagnostics, reference-objective
deviations, clocks, source references and paired comparisons. The
[final accounting](data/external-baseline-native-accounting-v1.json) and
[acceptance receipt](data/external-baseline-native-acceptance-v1.json) close this
continuation. The [previous report](lp-external-baseline-gpup-baseline.md), all
previous failures and every historical charge remain unchanged.

## Meaning of a pass

For cuOpt, the requested pass means a returned Solution with zero error status,
an empty error message and a recognized non-error termination. **90/96**
cuOpt trials have that observation. Iteration/time limits are accepted native
returns under this policy, but remain limits rather than native optimality.
NumericalError is a reported error even when the separate error-code field is
zero. A native return can survive a later checker/worker failure; its pass remains
logged while its successful complete-latency observation is unavailable.

Other configurations retain strict certification for comparison acceptance.
This deliberately asymmetric policy follows the user's request. Native-return
comparisons are **not quality-matched certified speedups**. Strict certificates
still use original-model feasibility, outward dual bounds and the unchanged
absolute/relative 1e-9 gap policy. GPU confirmation remains separate, including
unknown execution for short activity samples or presolve-only returns.

| Configuration | Attempted | cuOpt native-return passes | Complete comparison passes | Strict certificates |
| --- | ---: | ---: | ---: | ---: |
| project-tuned-fp64 | 24/24 | not this policy | 21/24 | 21/24 |
| project-precision-fp64 | 24/24 | not this policy | 21/24 | 21/24 |
| highs-cpu | 24/24 | not this policy | 15/24 | 15/24 |
| cuopt-pdlp-double | 24/24 | 24/24 | 24/24 | 9/24 |
| cuopt-pdlp-mixed | 24/24 | 24/24 | 24/24 | 3/24 |
| cuopt-pdlp-single | 24/24 | 24/24 | 24/24 | 3/24 |
| copt-cpu-pdlp | 24/24 | not this policy | 21/24 | 21/24 |
| copt-gpu-pdlp | 24/24 | not this policy | 18/24 | 18/24 |
| cuopt-concurrent | 24/24 | 18/24 | 15/24 | 9/24 |
| copt-cpu-default | 24/24 | not this policy | 15/24 | 15/24 |

## Complete delivery times

The following medians are seconds from fresh worker launch through durable
evidence and exit. A number requires all three accepted complete repetitions;
otherwise the certified/accepted count is shown and no successful median is
reported. No failure is dropped to improve a timing.

The six retained configurations use strict certification:

| Model | project-tuned-fp64 | project-precision-fp64 | highs-cpu | copt-cpu-pdlp | copt-gpu-pdlp | copt-cpu-default |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dense_block-1024 | 3.330 | 3.322 | 2.920 | 3.041 | 4.399 | 3.082 |
| irregular-2048 | 4.323 | 4.305 | 13.993 | 3.598 | 4.439 | 6.573 |
| scaling-256 | 2.296 | 2.300 | — (0/3) | 1.641 | 2.401 | — (0/3) |
| scheduling-20x5 | 3.332 | 3.334 | 1.707 | 1.768 | — (0/3) | 1.728 |
| small-4 | 2.297 | 2.309 | 1.296 | 1.344 | 2.409 | 1.344 |
| dense_block-65536 | 26.458 | 28.503 | 52.608 | 24.341 | 25.574 | 48.228 |
| irregular-32768 | 10.347 | 10.355 | — (0/3) | 8.577 | 9.439 | — (0/3) |
| mixed-65536 | — (0/3) | — (0/3) | — (0/3) | — (0/3) | — (0/3) | — (0/3) |

cuOpt uses the newly requested native-return policy in this separate table:

| Model | cuopt-pdlp-double | cuopt-pdlp-mixed | cuopt-pdlp-single | cuopt-concurrent |
| --- | ---: | ---: | ---: | ---: |
| dense_block-1024 | 3.635 | 6.681 | 6.652 | 2.627 |
| irregular-2048 | 2.609 | 4.599 | 4.609 | 4.606 |
| scaling-256 | 2.579 | 4.595 | 3.616 | 2.563 |
| scheduling-20x5 | 3.644 | 7.693 | 3.740 | 2.584 |
| small-4 | 2.634 | 2.610 | 6.667 | 2.646 |
| dense_block-65536 | 25.725 | 29.791 | 27.781 | — (0/3) |
| irregular-32768 | 10.653 | 12.666 | 12.682 | — (0/3) |
| mixed-65536 | 21.766 | 24.769 | 23.738 | — (0/3) |

For comparison with delivery overhead, cuOpt's reported **native solve** medians
are below. They require three error-free native returns, may include ordinary
iteration/time limits, and exclude preparation, import/export and independent
checking. They are diagnostics, not substitutes for the primary timings above.
The retained project interface does not isolate an equivalent native duration.

| Model | cuopt-pdlp-double | cuopt-pdlp-mixed | cuopt-pdlp-single | cuopt-concurrent |
| --- | ---: | ---: | ---: | ---: |
| dense_block-1024 | 0.828786 | 4.230006 | 3.727457 | 0.420628 |
| irregular-2048 | 0.314654 | 1.948722 | 1.592109 | 1.347595 |
| scaling-256 | 0.372232 | 1.926411 | 1.462655 | 0.211840 |
| scheduling-20x5 | 1.083522 | 4.891586 | 1.440392 | 0.464193 |
| small-4 | 0.325358 | 0.172581 | 3.953878 | 0.013594 |
| dense_block-65536 | 0.411001 | 4.150741 | 2.404825 | — (0/3) |
| irregular-32768 | 0.315947 | 2.981607 | 2.286907 | 48.800000 |
| mixed-65536 | 0.351459 | 3.921382 | 3.528156 | — (0/3) |

Old small-model results used v2 transport; new cuOpt results use v5's compiled
validation and buffered certificate output. Those cross-cohort paired ratios are
withheld. Large-model v4 and v5 share the same numerical worker/checker pipeline;
the new cuOpt raw-status/vector output is included in its delivery cost. The
machine report labels transport and quality matching for every comparison.
Complete three-pair comparisons use median log ratios and 10000 bootstrap
resamples with seed 17111. Three repetitions do not establish broad reliability.

## Numerical differences retained honestly

These maxima summarize observed diagnostics across different models and scales;
they are not a common accuracy target or a solver ranking. The allowance ratio
is original row-side violation divided by that side's original allowance; values
above one fail that componentwise test. A gap alone is not a certificate when
feasibility fails. Missing checker results stay unavailable.

| cuOpt configuration | Native termination counts | Feasible / checker observations | Largest row allowance ratio | Largest enclosed gap |
| --- | --- | ---: | ---: | ---: |
| cuopt-pdlp-double | Optimal: 24 | 12/24 | 11.4327 | 0.000596464 |
| cuopt-pdlp-mixed | IterationLimit: 21, Optimal: 3 | 3/24 | 1.69818e+07 | 10900.8 |
| cuopt-pdlp-single | IterationLimit: 24 | 3/24 | 8.54194e+07 | 1.14172e+09 |
| cuopt-concurrent | NumericalError: 3, Optimal: 15, TimeLimit: 3, unavailable: 3 | 12/15 | 86753.6 | 1.39753e-05 |

The machine evidence preserves available native objectives/residuals/gap, raw
vendor dual vectors and independently recomputed objective/bound/feasibility.
Missing values and partial deliveries remain explicitly unavailable.
Objective deviation from the matched project result is explicitly a deviation,
not an optimality gap when feasibility is absent. No vectors or tolerances are
silently repaired. The earlier presolve-only maximization dual-sign discrepancy
remains an unresolved adapter mapping; these observations do not prove a cuOpt
implementation defect. Native stopping rules and the project's componentwise
certificate policy also differ.

## What the completed comparison changes

All 72 forced cuOpt PDLP returns pass the requested native policy. Double reports
Optimal in all 24 cases; mixed reports 21 iteration limits, and single reports
24 iteration limits. Concurrent mode adds three explicit numerical errors,
three normal time-limit returns followed by outer timeouts, and three outer
timeouts with no durable native return. Thus 90 cuOpt native passes yield 87
complete comparison passes, while only 24 results have strict certificates.

The largest mixed model has **zero strict certificates across all ten
configurations**. This is broader than cuOpt qualification. All six retained
project FP64 endpoints report a native limit (four time, two iteration limits)
and no finite certified bound;
the unchanged adapter encounters the nonzero CLI exit before exporting their
candidates. The [native-limit observations](data/external-baseline-native-observations-v1.json)
retain the raw endpoints and their project-internal assessments without turning
them into independent certificates. For the first tuned repetition, that internal
assessment reports primal feasibility, but its reduced-cost enclosure cannot
certify a finite contribution for variable 3's infinite bound. The first COPT CPU
and GPU PDLP results also lack a finite bound and each violate seven original
row sides; cuOpt double violates 67. A missing bound does not prove the model
unbounded. Candidate extraction on normal limits and bound authority for
unbounded variables both need explicit follow-up before a certified performance
claim on this model.

Preparation and evidence delivery remain major costs. On dense-65536, cuOpt
double's median native solve is 0.411 seconds versus 25.725 seconds for complete
delivery. Its mixed/single complete medians are 29.791/27.781 seconds, with weaker
certificate coverage. These observations do not establish a low-precision gain.
Together with COPT's retained native-versus-complete discrepancy, they support
measuring conversion, import, solve, export and checking separately, then reducing
those costs under explicit cold and prepared-model lifecycles. Three development
repetitions and unequal quality policies cannot support a general solver ranking.

## Resource and transport failures

- `screening-gpup-extension-dense_block-65536-0-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `NumericalError`; native-return pass `false`. Full certified latency is unavailable.
- `screening-gpup-extension-dense_block-65536-1-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `NumericalError`; native-return pass `false`. Full certified latency is unavailable.
- `screening-gpup-extension-dense_block-65536-2-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `NumericalError`; native-return pass `false`. Full certified latency is unavailable.
- `screening-gpup-extension-irregular-32768-0-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `TimeLimit`; native-return pass `true`. Full certified latency is unavailable.
- `screening-gpup-extension-irregular-32768-1-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `TimeLimit`; native-return pass `true`. Full certified latency is unavailable.
- `screening-gpup-extension-irregular-32768-2-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `TimeLimit`; native-return pass `true`. Full certified latency is unavailable.
- `screening-gpup-extension-mixed-65536-0-highs-cpu`: `guardian_cpu_wall_deadline`; native termination `unavailable`; native-return pass `none`. Full certified latency is unavailable.
- `screening-gpup-extension-mixed-65536-0-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `unavailable`; native-return pass `none`. Full certified latency is unavailable.
- `screening-gpup-extension-mixed-65536-1-highs-cpu`: `guardian_cpu_wall_deadline`; native termination `unavailable`; native-return pass `none`. Full certified latency is unavailable.
- `screening-gpup-extension-mixed-65536-1-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `unavailable`; native-return pass `none`. Full certified latency is unavailable.
- `screening-gpup-extension-mixed-65536-2-highs-cpu`: `guardian_cpu_wall_deadline`; native termination `unavailable`; native-return pass `none`. Full certified latency is unavailable.
- `screening-gpup-extension-mixed-65536-2-cuopt-concurrent`: `guardian_cpu_wall_deadline`; native termination `unavailable`; native-return pass `none`. Full certified latency is unavailable.

Timeouts and failures are settled attempted cells, not successful solves. All
partial native returns, vectors, logs and cleanup records remain available.
The original 15 uncertified screening outcomes are reused, including HiGHS's
missing-candidate error mapping and COPT's strict-gap/native-limit outcomes.
They were not retried or relabeled.

## Execution, validation and scope

The continuation reused all 123 previously completed screening trials and executed
only the 117 previously unexecuted cells. No strict admission or historical
numerical check/profile was rerun. Source admission confirms unchanged original
models, solver settings, non-cuOpt adapters, original checker binary, libraries,
device and CPU affinity. The cuOpt input/settings prefix through Solve is identical;
new code captures the explicit error/status API and raw return evidence.

Nine new policy/export tests pass, including a native pass with a rejected
independent certificate and a native return surviving extraction failure. A
tenth CPU-only check exercises the installed cuOpt Solution API without Solve or
a device call. Prior tests and hardware receipts are reused. Delivery checks are
recorded in the linked acceptance receipt. One metadata-rendering guard rejected
an assumption that all six project limits were time limits; retained evidence
shows four time and two iteration limits. A separate corrected renderer records
that distinction, with no numerical rerun and the full 120-CPU-second failure
charge preserved.

The new CPU allocation is bounded at 32000 supervisor seconds, separately from
closed historical CPU allocations. Total baseline GPU authority stays **3600
seconds**, including **1277.244626616** previously charged. The settled
total is **3091.995889713 GPU seconds**.
v5 has at most 2322 whole remaining GPU seconds; failures retain full reservations. Final
post-settlement usage is in the accounting link. Four CPU slots, one GPU lease,
the unchanged 40-second native/60-second outer limits and sampled memory/output
bounds apply throughout. The old GPU ledger is untouched.

This is a generated development LP baseline on the pinned RTX PRO 6000 Blackwell,
cuOpt 26.10.0, COPT 8.0.6 and HiGHS 1.11.0. Gurobi remains unavailable. No held-out,
MILP, general commercial-solver ranking or supported low-precision preset follows.
GPUP-8 remains incomplete and GPUP-9 remains gated. The
[roadmap](../plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10) records the next
resident-execution and simpler mixed-precision decisions.
