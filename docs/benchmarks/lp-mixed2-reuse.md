# MIXED2 changing-model reuse: reliability and complete-session confirmation

[SPEC-0039](../specifications/SPEC-0039-mixed2-reuse.md) / [ADR-0072](../decisions/ADR-0072-mixed2-reuse.md).
The isolated executor caches four independently checked original models with an identical matrix,
switches RHS/objective/bounds, and resets FP64 state on every request. Both native and FP4 receive
the same cache, CPU preparation overlap and worker placement. The CUDA image and numerical solve
body remain unchanged. Public defaults remain unchanged.

Confirmation status: **incomplete-confirmation**; **31 / 512 sessions**,
**992 solves / 992 original-model certificates**.
The new operational stop prevents a confirmation pass. Only one or two complete pairs remain
per comparison, giving no finite simultaneous confidence bounds. Generic complete-session
ratios are near parity; coupled ratios are descriptively about 1.03–1.06x. These are incomplete
observations, not established speedups or evidence that the availability problem is repaired.
The earlier SPEC-0038 cohort remains incomplete and is never pooled, retried or regraded.

## Complete 32-request sessions

Each fresh session cycles four distinct RHS/objective scenarios eight times at one final tier.
The primary endpoint includes model parsing, checker/cache/representation preparation, switching,
all solves and independent certification, durable response delivery, EOF and destruction.
These are constructed finite-scenario streams, not production traces or warm-start solves.

| Family | Tier | Native session ms | FP4 session ms | Paired speedup [simultaneous interval] | Saved ms [interval] | Scoped value criterion |
| --- | --- | ---: | ---: | --- | --- | --- |
| dense-coupled-1024 | certified-1e-7 | 5067.132 | 4797.133 | 1.056 [unbounded, unbounded] | 269.999 [unbounded, unbounded] | not established |
| dense-coupled-1024 | certified-1e-9 | 6080.763 | 5730.803 | 1.061 [unbounded, unbounded] | 349.960 [unbounded, unbounded] | not established |
| dense-coupled-2048 | certified-1e-7 | 15450.482 | 14975.082 | 1.032 [unbounded, unbounded] | 475.400 [unbounded, unbounded] | not established |
| dense-coupled-2048 | certified-1e-9 | 18561.521 | 17894.916 | 1.037 [unbounded, unbounded] | 666.605 [unbounded, unbounded] | not established |
| dense-generic-1024 | certified-1e-7 | 2934.813 | 2954.725 | 0.993 [unbounded, unbounded] | -19.912 [unbounded, unbounded] | not established |
| dense-generic-1024 | certified-1e-9 | 2954.190 | 2886.440 | 1.023 [unbounded, unbounded] | 67.751 [unbounded, unbounded] | not established |
| dense-generic-2048 | certified-1e-7 | 9510.681 | 9447.501 | 1.007 [unbounded, unbounded] | 63.180 [unbounded, unbounded] | not established |
| dense-generic-2048 | certified-1e-9 | 9421.237 | 9457.674 | 0.996 [unbounded, unbounded] | -36.437 [unbounded, unbounded] | not established |

Ratios and savings are paired within block; marginal medians need not divide to the paired ratio.
Exact binomial median intervals cover eight ratios and eight absolute savings simultaneously
by Bonferroni (nominal at least 95%, conditional on independent session blocks). The shared GPU
and temporal conditions limit independence. Within-session requests are not independent samples.
The predeclared 32-block interval uses rank 8; at least 25 blocks must exceed a threshold for its lower bound to exceed it.
The 10 ms/session absolute floor (0.3125 ms/request) is an exploratory workload-value criterion,
not a user production SLO. A scoped pass requires complete coverage, all certificates, a speedup
lower bound above parity and a savings lower bound above 10 ms. The provisional 1.10x comparison
is reported in the machine analysis; neither criterion automatically authorizes adoption.
Every block, first-16 sensitivity and pair-order split remains visible. No scientific retry.

## Component costs and preparation

| Family / tier | Native / FP4 setup ms | Native / FP4 request ms | Native / FP4 GPU-phase ms | Native / FP4 physical updates |
| --- | ---: | ---: | ---: | --- |
| dense-coupled-1024 / certified-1e-7 | 1587.379 / 1650.034 | 102.500 / 92.399 | 28.356 / 17.856 | [600] / [600] |
| dense-coupled-1024 / certified-1e-9 | 1627.467 / 1684.711 | 132.932 / 120.498 | 37.807 / 23.805 | [800] / [800] |
| dense-coupled-2048 / certified-1e-7 | 5894.648 / 6152.275 | 286.876 / 266.075 | 52.920 / 28.016 | [600] / [600] |
| dense-coupled-2048 / certified-1e-9 | 6025.414 / 6168.505 | 380.969 / 351.934 | 70.583 / 37.344 | [800] / [800] |
| dense-generic-1024 / certified-1e-7 | 1621.325 / 1749.407 | 35.494 / 32.121 | 9.449 / 5.950 | [200] / [200] |
| dense-generic-1024 / certified-1e-9 | 1625.218 / 1649.094 | 36.019 / 33.169 | 9.448 / 5.950 | [200] / [200] |
| dense-generic-2048 / certified-1e-7 | 5989.992 / 6175.242 | 99.218 / 91.311 | 17.644 / 9.341 | [200] / [200] |
| dense-generic-2048 / certified-1e-9 | 5907.516 / 6166.744 | 99.183 / 93.946 | 17.649 / 9.340 | [200] / [200] |

For the largest strict coupled stream, aggregate complete-session cost shares are:

- native: setup 32.5%, independent checker 42.6%, original audit 8.0%, delivery/bookkeeping 2.9%.
- fp4x2: setup 34.5%, independent checker 45.2%, original audit 8.4%, delivery/bookkeeping 3.1%.

These are measured nonoverlapping aggregate host-clock partitions. GPU events are nested
diagnostics and are not added to this partition. Removing a component is not an attainable-speedup claim.

Request times include model switching and durable solve delivery. GPU values enclose submitted
windows, including launches and host gaps; they are not isolated tensor throughput. All work,
local-budget recoveries, promotions and checkpoint state are retained. Small-family historical
regressions are unchanged; this study selects no universal FP4 replacement or cold-solve preset.

Version 1 prepared four 2048 scenarios serially in roughly 10–11 seconds. Version 2 starts the
independent CPU checker while preparing the host model; both controls receive this overlap.
Observed version-2 admission preparation is roughly 6.0–6.6 seconds. In the available strict
coupled2048 FP4 sessions, setup and independent checking together consume about 80% of full
session time. This leaves exact host preparation/checking as larger cost targets than tensor
arithmetic, after the availability problem is resolved.
Original-model admission still precedes CUDA. The versioned admission measurements are exploratory,
not an independent causal performance confirmation. Version 1 and its deadline refusal remain visible.

## Reliability diagnosis

A fresh CPU-only fixture preparation again missed the unchanged 100 ms heartbeat, despite limiting
numerical workers to three CPUs. GPU execution is therefore not a necessary trigger. Separating
guardian/coordinator placement onto the fourth CPU is a mitigation, not an availability guarantee.
The successful instrumented preparation reached a 75.5 ms sampling gap. Its largest observed
heartbeat gap was about 63.3 ms, with about 53.0 ms accumulated coordinator runqueue wait. These
are different timer boundaries; the scheduling observation is from a successful run, not the
historical failed instant. Instrumentation disturbance and shared-host activity remain limitations.

A later independent serial CPU reassessment also missed the heartbeat with pinned controls.
That failed reservation retains its partial certificates and full charge. A new diagnostic
reassessment with supervisor and parent scheduling telemetry passed all retained requests;
this does not establish why the uninstrumented attempt failed or prove pinning sufficient.

All sixteen predeclared racecheck probes passed across historical/current hosts, native/FP4,
all-process/application-only instrumentation and both CPU placements. The earlier exit 11 did not
reproduce. This is not a root-cause finding or proof of repair. New scoped sanitizer admission
covers the root CUDA executor; the independent checker is separately CPU-admitted. No production-
readiness claim follows. Primary confirmation uses no added supervisor telemetry and retains the
original supervisor source, 100 ms limit, resource ceilings and cleanup requirements.

## Acceptance, failures and reproducibility

Full CPU/native acceptance: 638 repository Rust / 706 Python tests, plus 28 isolated Rust tests,
Clippy, dependency audit, native replay, artifact validation, documentation and smoke. The current
host also receives CPU original-endpoint/norm admission, 130 device cases / 2304 rational outputs,
four arithmetic/lifecycle sanitizer suites and four scenario-switch sanitizer suites. Cached
scenarios, repeated returns, recovery and native promotion are compared with fresh sessions.
All retained final/audit points covered by serial validation are reassessed using the original
independent serial checker; portable timing replay is a separate check, not a new solver run.

Failed development reservations preserve sources, partial output and full charges. The 128 MiB
legacy reader refusal was corrected to the admitted 384 MiB model cap. A three-CPU launch of the
repository gate incorrectly prevented its four-CPU supervisor tests; the full gate subsequently
passed with four CPUs. The first all-family scenario admission reached its reserved work deadline;
subsequent admission is split by family. An additional full-trajectory scenario racecheck also
reached its work deadline. The final scenario sanitizer suite uses bounded switch/reset/step/
restore comparisons, while full converged trajectories are separately admitted. The complete
original 97-case arithmetic/lifecycle suite remains covered by every sanitizer. None of these
development corrections replaces a scientific sample.

[Analysis](data/mixed2-reuse-analysis-v1.json), [portable session records](data/mixed2-reuse-records-v1.json).
Replay: `python3 tools/lp_mixed2_reuse_analysis.py verify`.
The archives retain original responses and model inputs, all failed versions and resource receipts.
Historical source/evidence and prior handoffs remain exact. GPUP-8 remains incomplete; GPUP-9 gated.
Further production evaluation needs representative workload traces and an explicit disposition
of the unresolved process/scheduling reliability limits. No follow-on allocation is released.

## Complete coverage and reliability disposition

Retained responses: 1018; 992 belong to completed sessions and 26 are partial-session files.
Missing session cells: 481. Failed block indices (zero-based): [1, 2].
Unattempted block indices after the operational stop: [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31].
[Retained-record diagnosis and full block ledger](data/mixed2-reuse-diagnosis-v1.json).

After the operational stop, the bounded CPU preparation probe completed 9 model preparations with external parent telemetry and the original supervisor. Its result is passed; maximum supervisor sampling gap is 15.807 ms.
The probe does not reproduce the failed instants or establish a repair. Observer gaps and
shared-cgroup throttle/memory counters remain in the diagnosis; they are separate boundaries.
No CPU-throttle counter increase was observed during these successful probe phases;
this does not establish the counter behavior at either failed scientific instant.

The frozen cohort is incomplete. All intervals describe available complete pairs,
conditional on observed coverage; missingness may be informative. No scoped confirmation,
retention or adoption pass is claimed. Failed blocks are not retried. Two consecutive
untouched blocks failed supervision, so the remaining 29 blocks were not launched.
This operational stop was independent of measured speedup. The frozen source and
analysis remain exact; a separate explicit coverage adapter records unattempted cells
without inventing resource reservations or regrading the frozen criterion.

| Block index | Supervisor reason | Complete sessions | Full CPU / GPU charge seconds |
| ---: | --- | ---: | ---: |
| 1 | lost_coordinator_heartbeat | 0 | 800.000 / 200.000 |
| 2 | lost_coordinator_heartbeat | 15 | 800.000 / 200.000 |

The prospective CPU placement mitigation did not eliminate heartbeat failures.
Primary timings contain no added supervisor telemetry, so the failed instants remain
unassigned. Further independent confirmation should follow a resolved and admitted
availability strategy; repeating scientific cohorts is not a substitute for diagnosis.

Independent serial validation covers 1778 response files / 5820 assessment requests / 197 distinct original-model endpoint/tier assessments. Portable evidence and timing replay pass without the original artifacts tree; 1957 historical files and every prior handoff/backlog entry remain exact.

Allocation closed at 25496.532357332 CPU / 1685.317121775 GPU seconds, including 128 closing CPU seconds. All cleanup is empty.
[Acceptance](data/mixed2-reuse-acceptance-v1.json), [accounting](data/mixed2-reuse-accounting-v1.json),
[portable development evidence](data/mixed2-reuse-evidence-v1.json), [resource receipts](data/mixed2-reuse-resources-v1.json.gz).
