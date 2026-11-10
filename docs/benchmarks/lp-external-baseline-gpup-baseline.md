# GPUP-BASELINE: implemented comparison harness and bounded results

Date: 2026-11-10. Status: implementation delivered; full scientific comparison
incomplete. Six configurations pass admission. Of 240 planned screening cells,
123 execute and 108 certify; 96 are blocked by cuOpt admission and 21 remain
unexecuted because a complete reservation cannot fit the CPU screening allocation.
GPUP-8 remains incomplete and GPUP-9 stays gated. Gurobi is unavailable.

The [machine summary](data/external-baseline-result-v1.json) binds the frozen
manifest, complete roster, comparisons, endpoint diagnostics and retained failed
reservations. The [final accounting](data/external-baseline-final-accounting-v1.json)
is authoritative after all reporting jobs settle. Raw evidence is in
`artifacts/gpup-external-baseline-v1` through `v4`; these are immutable local run
artifacts, not dependencies downloaded by the documentation build.

## What was implemented

The isolated harness implements [SPEC-0022](../specifications/SPEC-0022-external-lp-baseline.md):
lossless canonical input, exact vendor readback, original-unit primal/dual export,
a solver-neutral Rust checker, immutable source/library/model bindings, deterministic
ordering, resource reservations, GPU execution evidence and paired comparisons.
The checker calls the retained original-model evaluator, outward dual certificate
and gap predicate with absolute and relative tolerances 1e-9. Native `optimal`
alone never certifies a row. Native limits may certify only when transport finishes
and the independent checker accepts the endpoint.

The ten configurations are two retained project FP64 paths, HiGHS CPU, cuOpt PDLP
double/mixed/single and concurrent, COPT CPU/GPU PDLP, and COPT CPU default.
Versions are cuOpt 26.10.0, COPT 8.0.6 and HiGHS 1.11.0. The device is RTX PRO
6000 Blackwell Server Edition, UUID `GPU-6721b13a-30f9-83ec-dace-ba2d9738556f`,
driver 580.105.08. CPU affinity is logical CPUs 0–3. Retained project/HiGHS APIs
support one native thread; vendors request four. This is an equal available CPU
envelope with explicit native-thread differences, not an equal-thread experiment.

Two admission suites per configuration each require four tiny min/max,
ranged/equality, objective-offset cases followed by a nontrivial original model.
Forced PDLP needs useful nonzero work; GPU claims need affirmative execution
evidence. Twelve suites pass, four refuse, and four dependent suites remain
unexecuted. The six admitted configurations enter screening unchanged.

Primary latency spans fresh worker launch through durable endpoint, certificate
and worker exit. It includes conversion/import/export/checking and evidence I/O.
Native solve time is a diagnostic, never a replacement. Each screening job has
40 seconds for the native solve and 60 outer seconds including two cleanup seconds.
See [operations](../operations/lp-external-baseline.md) for commands and containment.

## Certified screening results

Entries are median complete seconds, shown only when all three repetitions
certify. Fractions denote certified/planned repetitions and carry no timing claim.
`0/3*` means unexecuted; other incomplete entries include their failures in the
denominator. The small models use retained v2 transport and large models use v4;
every within-model pair uses the same transport version.

| Model | Project tuned | Project precision FP64 | HiGHS CPU | COPT CPU PDLP | COPT GPU PDLP | COPT CPU default |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| small-4 | 2.297 | 2.309 | 1.296 | 1.344 | 2.409 | 1.344 |
| dense-block-1024 | 3.330 | 3.322 | 2.920 | 3.041 | 4.399 | 3.082 |
| irregular-2048 | 4.323 | 4.305 | 13.993 | 3.598 | 4.439 | 6.573 |
| scaling-256 | 2.296 | 2.300 | 0/3 | 1.641 | 2.401 | 0/3 |
| scheduling-20x5 | 3.332 | 3.334 | 1.707 | 1.768 | 0/3 | 1.728 |
| dense-block-65536 | 26.458 | 28.503 | 52.608 | 24.341 | 25.574 | 48.228 |
| irregular-32768 | 2/3 | 2/3 | 0/3 | 8.577 | 2/3 | 0/3 |
| mixed-65536 | 0/3* | 0/3* | 0/3* | 0/3* | 0/3* | 0/3* |

All four cuOpt configurations have zero screening executions, accounting for 96
planned cells. The other 21 unexecuted cells are all 18 mixed-model cells plus
repetition 2 of the project tuned, project precision and COPT GPU configurations
on irregular-32768. No passed or refused screening result is discarded.

There are 27 complete three-pair comparisons against project tuned. For the
dense-65536 model, the ratios below are project time divided by candidate time;
a ratio above one favors the candidate. Intervals are the predeclared 10000-resample
paired log-ratio bootstrap with seed 17111. With only three pairs, they describe
this small sample and do not establish broad performance reliability.

| Candidate | Median paired ratio | 95% bootstrap interval |
| --- | ---: | ---: |
| Project precision FP64 | 0.927 | 0.898–0.929 |
| HiGHS CPU | 0.503 | 0.499–0.509 |
| COPT CPU PDLP | 1.089 | 1.028–1.090 |
| COPT GPU PDLP | 1.034 | 1.034–1.037 |
| COPT CPU default | 0.549 | 0.547–0.562 |

This generated development corpus supports per-model observations only. It does
not rank commercial solvers on real-world LPs, establish Tensor execution, compare
MILP search, or select a supported precision preset. No held-out model was used.

## Quality and mapping refusals

cuOpt executes on the installed CUDA stack; installation incompatibility is not
the reason for these exclusions. Matching parameter names and nominal 1e-9 values
does not make vendor termination rules equivalent to the original checker.

| Configuration | Retained admission witness | Consequence |
| --- | --- | --- |
| cuOpt PDLP double | Four tiny cases pass. Irregular-2048 returns native optimal after 610 iterations, but four row sides violate the original componentwise feasibility policy; one violation is about 2.11 times its allowance. | Not admitted. Short-run GPU activity is also unconfirmed for that endpoint; no timing comparison follows. |
| cuOpt PDLP mixed | Four tiny cases pass. Irregular-2048 reaches 50000 iterations with confirmed GPU work, 454 violating row sides and an independently enclosed gap about 9.479. | Not admitted; low-precision work alone is insufficient. |
| cuOpt PDLP single | The tiny maximization/equality case reaches 50000 iterations. Primal is feasible, but the dual yields gap 1.19209e-7 at objective 4.25. | Not admitted under the unchanged 1e-9 policy. |
| cuOpt concurrent | PSLP entirely eliminates the tiny maximization/ranged model. The exported normalized row multiplier is +1 where the admitted convention requires -1; gap is 3. Native `solved_by=5` is unset. | Unresolved presolve/postsolve mapping, not proof that the vendor solved the LP incorrectly. No global sign flip or silent repair. |

The 15 uncertified screening results have five distinct causes, each repeated
three times:

- HiGHS scaling-256 records native `run_error` / `backend_failure` without a
  candidate. The adapter's unconditional candidate lookup then records a
  `KeyError`; the raw native record is retained. This is unavailable evidence,
  not a measured quality-adjusted win. Error mapping needs a focused correction.
- COPT CPU default scaling-256 returns native optimal and a feasible primal,
  but the independent bound leaves a gap of about 19.0411 at objective -1.21358e8.
- COPT GPU PDLP scheduling-20x5 returns native optimal and a feasible primal,
  but gap 1.94407e-6 exceeds the declared tolerance at objective about 1184.
- HiGHS irregular-32768 reports a numerical failure and an infeasible endpoint.
- COPT CPU default irregular-32768 reaches its 40-second native limit without
  primal/dual evidence. Outer transport completes, but certification is unavailable.

No admission or checker refusal is repaired by a hidden second optimization run.
These outcomes remain inputs to the [next protocol decisions](../plans/gpu-lp-precision-roadmap.md#baseline-follow-up-decisions).

## Bottlenecks exposed by the new baseline

The first dense-65536 repetition makes the delivery overhead visible:

| Configuration | Native solve, seconds | Independent checker, seconds | Complete worker, seconds |
| --- | ---: | ---: | ---: |
| Project tuned | unavailable separately | 4.659 | 26.430 |
| Project precision FP64 | unavailable separately | 4.426 | 28.503 |
| HiGHS CPU | unavailable separately | 4.579 | 51.952 |
| COPT CPU PDLP | 1.194 | 4.209 | 24.242 |
| COPT GPU PDLP | 0.574 | 4.326 | 25.574 |
| COPT CPU default | 23.812 | 4.324 | 47.015 |

COPT's native GPU PDLP call is faster than its CPU call here, while complete GPU
delivery is slower. This is an observed distinction between algorithm time and
the measured fresh-worker pipeline. The difference includes model conversion,
import, library startup, readback, export and evidence; it is not all GPU launch
overhead. The retained project interface does not isolate its native solve time,
so no native-only cross-solver speedup is inferred.

The harness itself initially obscured the large-model experiment. A global
16 MiB file limit wrongly applied the log limit to certificate artifacts. After
separating those limits, generic schema walks and unbuffered pretty-JSON output
still exhausted the unchanged outer deadline. v4 uses a pinned compiled validator
for two flat schemas and a 1 MiB buffered checker writer with flush/fsync. A
CPU-only preflight converts the 103743588-byte dense original to the byte-exact
49357176-byte canonical record in 10.045 seconds. The mathematical assessment
function and strict parser are byte-identical to the original new checker.

These corrections make the measurements usable, but the remaining host/evidence
cost limits what faster arithmetic can achieve in this pipeline. The roadmap
therefore requires explicit cold/prepared lifecycles and phase attribution before
claiming benefits from another precision or residency change. This new harness
finding does not replace the earlier GPUP-8 reconstruction/update diagnosis.

## Resources, preservation and validation

The user authorized implementation and 3600 additional GPU seconds.
[ADR-0048](../decisions/ADR-0048-external-baseline-execution.md) allocates the
bounded study; [ADR-0049](../decisions/ADR-0049-baseline-adapter-correction.md),
[ADR-0050](../decisions/ADR-0050-baseline-artifact-transport.md) and
[ADR-0051](../decisions/ADR-0051-baseline-cpu-transport-cost.md) record each separate
engineering correction and evidence reuse. GPU charge is **1277.244626616 / 3600**
seconds, including full failed reservations. GPU time is leased elapsed time or
the full failure reservation, not kernel-active time.

Current CPU phase caps total 16000: implementation 2700, hardware 240, admission
2400, screening 9860, reporting 600 and restricted cleanup 200. Screening charges
9775.536859960 CPU seconds; the next whole job requires 240 and cannot fit.
Unused GPU or other phase headroom does not silently become screening CPU funds.
Final post-report CPU totals and remaining funds are in the linked accounting.

All four versions and every charge remain. In particular, the initial build/API
failures, one cancelled v2 large-model CPU trial charged 240, sixteen v3 large-model
timeouts charged 3840, and the compiled-validator boolean-constant test failure
charged 80 are retained. The cancelled worker's lost guardian is recorded with
its explicit coordinator cleanup and full settlement; it is not relabeled passed.
The first delivery metadata check also retains its full 280-CPU-second failure
charge: it applied the run-artifact root restriction to two explicitly pinned
read-only API files under `/root/copt80`. A separate metadata-only correction
hashes those paths directly and completes the remaining checks, reusing the
already completed freeze/history checks. No solver or installed file changes.
The v4 source freeze reuses the six COPT admission passes, completed hardware
checks, subsequent project/HiGHS admissions and all five small-model blocks.
No cuOpt numerical refusal or passed historical scientific check is rerun.

Twenty-five new Python tests and one buffered-writer Rust test pass, covering
strict witness admission, bounds/identity/status refusal, reservation boundaries,
actual adapter calls, log containment, schema equivalence and exact immutable
serialization. The earlier twenty SPEC tests are reused. Scoped Rust formatting,
Clippy and builds pass. Full historical native/device gates are not rerun.
The [delivery acceptance](data/external-baseline-acceptance-v1.json) records source,
dependency, documentation, cleanup and historical-evidence checks.
All 184 documentation pages/internal links and 50 acyclic backlog tasks pass;
fifteen historical evidence files and twelve inspected API sources remain exact.

The original numerical crates, CUDA code and historical research implementations
remain unchanged. The historical 17438-event GPU ledger retains SHA-256
`fabe2e22047bac9194867e1f745c627a2271bc7c0cd283f17b207957c7bbb59d`;
the new baseline never appends to it. No supported backend defaults, GPUP-8
completion criteria or GPUP-9 gate are changed.
