# GPUP-6: audited adaptive FP32/FP64 recovery

Status: implementation accepted on 2026-09-26 under
[ADR-0025](../decisions/ADR-0025-adaptive-precision-recovery.md) and
[SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md). The development
comparison is deliberately reported with failed and missing evidence. No supported
preset, held-out winner, or general solver superiority claim is selected.

## Contract and numerical authority

`cuda-lp-tuned --lp-adaptive` accepts strict version-1 policies, mutually exclusive
with fixed `--lp-precision`. Every policy explicitly names its ordered ladder,
audit interval, separate primal/dual absolute tolerances, relative tolerance,
and either disabled demotion or its clean-window count and margin fraction.
The five available rungs are FP32 working state, FP32 accumulation with FP64 state,
FP32 products with FP64 accumulation, FP32 matrix storage with FP64 arithmetic,
and original-operator FP64. Ladders can skip rungs and must end at FP64.

The host owns the adaptive controller and CPU arithmetic mirror. Operators are
prepared independently from the canonical matrix, with one conservative step
valid throughout the solve. A complete window-start checkpoint preserves iterates,
anchors, weight, controller errors, restart history and logical counters. Windows
close at an audit or controller assessment boundary. Failed guards/audits restore
the whole window and promote one configured rung; replay targets the same logical
endpoint. Preparation guards mark unavailable rungs explicitly. Device residency
is recreated at transitions, with peak admission and cumulative allocations
reported separately.

The final update is recomputed in original-operator FP64 from the pre-step state
saved before working-state narrowing. Both original-unit vectors must satisfy
`abs(low-reference) <= absolute + relative*max(abs(pre_step),abs(reference))`.
Nonfinite comparisons fail. Passing audits adopt the reference endpoint. A demotion
requires a charged prospective lower-rung CPU update satisfying a stricter margin;
its numerical result is discarded. Neither audit agreement nor recovery supplies
a bound: original-model host feasibility and conservative certification remain
authoritative, preserving the GPUP-1 exact-rational regressions.

Physical work equals proposals plus reference audits plus demotion probes.
Rejected proposals and replay are overlapping diagnostic subsets of proposals,
not extra additions to that total. Closing-audit work is reserved before proposing;
chunks contain at most 64 updates and isolate the final update. Rollback never
refunds work or time. Limits/interruption preserve committed and previously
validated results; device failure follows the existing pinned-HiGHS availability
fallback contract separately from numerical promotion.

Version-5 solve records/endpoints bind requested policies, execution/code identity,
per-rung proposals, transitions, audit/probe/window counts and profiling phases.
The kernels, prior code-object bytes, legacy record behavior and frozen protocols
are unchanged. Adaptive sessions, persistent restart files, research component
arithmetic, quantization, FP8, Tensor Cores and portfolios are outside this slice.

## Frozen comparison

The protocol is `benchmarks/configs/lp-adaptive-v1.json`, identity
`gpup6-adaptive-v1`: the original twelve development instances and four profiling
instances, three paired timing repetitions, seeds 17001/17002 and solve seed 17,
10-second solve limit, 50000 physical updates, unchanged method settings and final
1e-9 tolerances. Primary timing is fresh-process certified single-solve latency,
including initialization, audits, replay, transfers and original-model certification.
Profiling is separate and never pooled into primary timing.

| Ordered block | Frozen configurations | Planned attempts |
| --- | --- | ---: |
| Coverage | Six established controls, five fixed-precision controls, adaptive FP64, fourteen interval-32 strict recovery policies; twelve instances x three repetitions | 936 |
| Policy interactions | Seven ladders x four intervals x two audit profiles x two recovery policies, plus six FP64 controls; four instances x three repetitions | 1416 |
| Separate profiles | Tuned FP64, adaptive FP64, sticky accumulation-to-FP64 intervals 1/32/128, gradual working-state demotion; four instances | 24 |

The seven ladders are four direct-to-FP64 choices and gradual ladders containing
all remaining rungs from working state, accumulation, or products. Audit intervals
are 1/8/32/128; all three audit tolerances are 1e-7 or 1e-5; recovery is sticky or
demotion after four clean windows with a 0.25 margin. Configurations are randomized
reproducibly within instance/repetition blocks before timing. No values changed
after timing began.

The machine is the retained RTX 5090 (`GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48`),
using the shared one-device host lease and pinned HiGHS 1.11.0. The supervisor binds
one CPU and records process-tree memory; actual process times and lease charges
are distinct. The source/executable/code images and native-gate receipt were
archived before admission. Rust/compiler version lookup in the study launcher was
unavailable because its shell PATH omitted Cargo; the native gate and exact source
and executable hashes are retained, rather than inventing version strings.

## Retained harness failures

The first preflight had an obsolete v5 trial configuration enum and failed before
any admission or GPU work. Its archive remains under
`artifacts/gpup6-adaptive-v1-preflight-01`. The schema was corrected, a synthetic
pre-admission test was added for every frozen configuration, and the complete
native gate passed again before measurements.

The next launch omitted `schedule_eval.cubin` from the code archive. Device
discovery requires that existing image even for LP solves. GPU trials failed before
LP execution; those attempts, their stderr and their lease charges remain in the
comparison. The coordinator was stopped and the unchanged image copied into the
archive; `archive-repair.json` pins its hash. Only previously unattempted identities
were resumed, with the same measured source, executable, numerical settings and
LP kernels. No failed trial was retried or replaced. Final tooling includes the
discovery image in archive preflight and tests its presence before admission.

These losses make the affected coverage cells unavailable, not evidence against
any arithmetic policy. They must remain visible in both denominators and pairing.
Only certified, completed, non-fallback pairs contribute timing ratios. Confidence
intervals use the frozen paired bootstrap, seed 17002 and 10000 resamples; three
repetitions offer limited uncertainty information and cannot select a preset.

## Coverage and independent verification

All **2376/2376** planned attempts were admitted; no scheduled identity is missing.
The archived executable and the final strengthened verifier independently accept
**2086/2086** available endpoints. This includes interrupted, work-limited,
numerically rejected and backend-failure evidence, not only certificates. The
comparison remains incomplete because 290 attempts have no endpoint: 288 discovery
failures, one cancelled worker and one interrupted coordinator intent. The latter
reservation is conservatively charged in full. No invalid endpoint was accepted.

| Block | Attempts | Verified endpoints | Certified completed outcomes | Other outcomes |
| --- | ---: | ---: | ---: | --- |
| Coverage | 936 | 646 | 429 | 150 work limits; 57 numerical rejections; 7 timeouts; 3 backend failures; 290 without endpoints |
| Policy | 1416 | 1416 | 1392 | 12 timeouts and 12 work limits |
| Separate profiles | 24 | 24 | 24 | None |

Coverage denominators retain all three repetitions on all twelve instances. All
GPU configurations lost the same first four instances to discovery (12 attempts
per configuration); CPU controls were unaffected by that missing image but include
the coordinator interruption. Policy-block results never replace lost coverage
cells, even where the policy names overlap.

| Coverage configuration(s) | Certified / planned, each |
| --- | ---: |
| Pinned HiGHS | 30 / 36 |
| Host LP | 27 / 36 |
| Legacy CUDA LP | 6 / 36 |
| Matched, tuned and precision FP64; adaptive FP64 interval 32 | 18 / 36 |
| Fixed storage, products, accumulation and master-correction-32 | 9 / 36 |
| Fixed working-state correction-32 | 6 / 36 |
| Each of the fourteen strict interval-32 adaptive recovery policies | 18 / 36 |

The adaptive policies recover the FP64 control's certified coverage on the
available coverage cells. The missing cells prevent a complete twelve-instance
comparison. In the separate policy block, every loss is a working-state-starting
policy with interval 1 and loose 1e-5 audits: direct or gradual, sticky or demoting,
all three repetitions time out on irregular-2048 and hit work limits on
dense_block-1024. The final 1e-9 tolerances stay unchanged.

The complete [comparison table](data/gpup6-comparisons.csv) records all 808
block/instance/configuration cells, including zero coverage, outcomes, absolute
medians and paired confidence intervals. It is derived from the independently
verified report; missing pairs have no ratio.

## Paired fresh-single latency

The following policies are the prespecified profiling selections, shown using
their separate policy-block timing repetitions. Each cell is tuned-FP64 latency
divided by candidate latency, with paired 95% bootstrap interval; all these cells
have three certified pairs. Values below one mean slower than tuned FP64. No
cross-instance pooling or multiple-comparison winner selection is performed.

| Candidate (strict audits) | small-4 | irregular-256 | irregular-2048 | dense-block-1024 |
| --- | ---: | ---: | ---: | ---: |
| Adaptive FP64, interval 32 | 0.953 [0.888, 1.142] | 1.001 [0.871, 1.151] | 0.767 [0.760, 0.843] | 0.893 [0.857, 0.932] |
| Accumulation to FP64, sticky, interval 1 | 0.948 [0.842, 1.143] | 0.817 [0.742, 0.817] | 0.298 [0.295, 0.304] | 0.440 [0.417, 0.440] |
| Accumulation to FP64, sticky, interval 32 | 0.974 [0.879, 1.167] | 0.948 [0.824, 0.977] | 0.774 [0.766, 0.848] | 0.917 [0.802, 0.918] |
| Accumulation to FP64, sticky, interval 128 | 1.005 [0.948, 1.204] | 0.960 [0.960, 0.970] | 0.853 [0.810, 0.868] | 0.898 [0.862, 0.918] |
| Gradual working state, demotion, interval 32 | 0.982 [0.817, 1.176] | 1.068 [0.968, 1.068] | 0.711 [0.693, 0.740] | 0.779 [0.741, 0.788] |

Tuned FP64 certified medians are 343.436, 437.666, 475.725 and 451.598 ms in
those four columns. Accumulation-to-FP64 interval 1 takes 362.261, 535.866,
1596.205 and 1026.695 ms; interval 32 takes 352.739, 461.659, 614.634 and
492.418 ms. Frequent audits are expensive on the larger instances: interval 1
is about 3.36x tuned latency on irregular-2048 and 2.27x on dense-block-1024.
The FP64-only adaptive controls show similar costs, so lower arithmetic width
alone does not explain the slowdown. Small-case intervals include one and do
not establish an improvement. These are development-only measurements with
three repetitions and incomplete coverage; no preset is selected.

## Cost interpretation

The separate profiling block records host preparation, original-operator audits,
prospective demotion probes, executor allocation/upload and kernel synchronization.
Transition costs include newly allocated residency and transfers; the execution
observations retain their cumulative counts. Rejected and replayed update counts
quantify discarded/repeated work. Replay executes through the ordinary kernel
phase, so its kernel time overlaps that phase and is not an additional measured
wall-time term. Controller checkpoint/rollback overhead remains inside complete
process latency; this implementation does not claim a separate stopwatch for it.
The profile CSV exposes every recorded phase rather than estimating an unmeasured
replay or transition-only latency.


Across all verified adaptive endpoints, proposals total 7924549, reference audits
1303076 and demotion probes 31409: **9259034 physical updates**. Rejected proposals
are 86558 and replay proposals 86557 (overlapping subsets). There are 1889 failed
audits/promotions and 131 demotions. No study run encounters a preparation/range
failure; fault-injection acceptance exercises those paths separately.

The following separate profiles cover sticky accumulation-to-FP64 on every
profiling instance. They are one run each, not timing confidence intervals.

| Instance | Audit interval | Physical work | Audits | Replay proposals | Audit ms | Kernel/synchronization ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| small-4 | 1 | 400 | 200 | 0 | 0.136 | 12.330 |
| small-4 | 32 | 207 | 7 | 0 | 0.007 | 4.189 |
| small-4 | 128 | 202 | 2 | 0 | 0.004 | 3.909 |
| irregular-256 | 1 | 2802 | 1401 | 1 | 57.440 | 103.554 |
| irregular-256 | 32 | 1482 | 50 | 32 | 2.700 | 31.508 |
| irregular-256 | 128 | 1543 | 15 | 128 | 0.935 | 30.396 |
| irregular-2048 | 1 | 3202 | 1601 | 1 | 888.046 | 205.470 |
| irregular-2048 | 32 | 1689 | 57 | 32 | 30.659 | 52.459 |
| irregular-2048 | 128 | 1745 | 17 | 128 | 9.320 | 48.770 |
| dense_block-1024 | 1 | 3602 | 1801 | 1 | 391.543 | 169.882 |
| dense_block-1024 | 32 | 1896 | 64 | 32 | 14.494 | 48.124 |
| dense_block-1024 | 128 | 1947 | 19 | 128 | 4.485 | 45.264 |

On irregular-2048, interval-1 host audits consume 888.046 ms versus 205.470 ms
in kernels/synchronization; interval 128 spends 9.320 ms on audits. Across all
24 profiles context creation is 227.570-314.511 ms. This fixed cost persists.

Gradual working-state demotion at interval 32 has the following separate profiles.
Allocation/upload time includes initial residency and all recreated residencies;
it is not an isolated estimate of promotion overhead.

| Instance | Transitions | Probes | Replay proposals | Probe ms | Allocation/upload ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| small-4 | 0 | 0 | 0 | 0.000 | 0.479 |
| irregular-256 | 4 | 1 | 128 | 0.048 | 2.206 |
| irregular-2048 | 6 | 8 | 160 | 5.491 | 5.005 |
| dense_block-1024 | 6 | 8 | 160 | 3.788 | 4.234 |

The [profile table](data/gpup6-profiles.csv) retains all 24 observations, every
phase, device peak memory and adaptive work counters.

## Scope limits carried forward

All comparisons use development data on one GPU. Audit tolerances bound one local
update discrepancy and do not prove global trajectory accuracy. Aggressive audit
intervals consume physical-update budget and host time; demotion can repeat a
promotion cycle and spend more work. Every endpoint is therefore assessed on the
original model, and a work limit or numerical failure cannot imply optimality.

Adaptive repeated-solve sessions and persistent checkpoints are unimplemented.
The previous 65536-row throughput timeouts and incomplete historical tuned_cases
racecheck receipt remain open. The four passing adaptive sanitizer scopes do not
retroactively close that older gap. Quantization and Tensor Core work require
later bounded contracts; no candidate becomes a supported recipe from this study.

One retained policy interaction illustrates the audit/certification distinction:
on irregular-2048, direct working-state FP32 to FP64, interval 1, loose 1e-5
profile and sticky recovery, repetition 0 times out at 10.148462419 s. Its 13653
proposals and 13653 reference audits all pass, with no rejected window or promotion,
yet original-model certification does not close at the final 1e-9 tolerances.
The interrupted endpoint verifies independently. Local update agreement therefore
cannot substitute for convergence or trigger an implicit success claim.

## Acceptance and resource accounting

The final implementation passes the full pinned-native `bash tools/check.sh`:
493 Rust results, 155 Python tests, strict formatting/lints, advisory/license
checks, legacy committed-record re-execution, artifact/schema validation and smoke
checks. Final documentation has 95 validated pages. Five adaptive protocol,
phase/cap/prefix/output-binding, crash-recovery and archive-admission tests also
pass from a clean source copy with no local campaign artifacts. Four build jobs
and the declared four-hour CPU validation budget were retained; command runtimes
are retained in the gate logs, but aggregate CPU-seconds were not instrumented.

Regular device acceptance passes 14 CUDA-boundary, 6 schedule and 35 LP device
tests with no skips. Four explicit adaptive policies pass CLI endpoint verification
and replay; exclusive flags and pinned fallback are covered. Both adaptive tests
pass memcheck, racecheck, initcheck and synccheck. Racecheck reports zero hazards,
errors and warnings; the other scopes report zero errors. A final complete repeat
of these gates passes after diagnostics/archive review. The final verifier also
accepts all 2086 endpoints from the measured executable.

The first regular-device acceptance failed because its new CPU test oracle never
stopped at an independently certified endpoint while the GPU backend did. The
fixture now performs original-model feasibility and certification at the same
controller boundaries; runtime arithmetic did not change. The failed receipt and
its 10.907562318 GPU seconds remain charged. Initial native/preflight failures
are retained as well; no skipped native or device gate is counted as acceptance.

| Allocation | Charged GPU seconds | Cap |
| --- | ---: | ---: |
| GPUP-6 comparisons / ablations | 1826.094392481 | 5400 |
| GPUP-6 acceptance / repeatability, including failed acceptance | 70.478730162 | 900 |
| GPUP-6 combined | 1896.573122643 | 6300 |
| Cumulative campaign | 8912.494084146 | 14402.574545061 authorized ceiling; 28800 campaign cap |

CPU comparison workers charge 146.060000196 seconds in the same ledger,
separately from GPU consumption. These charges are worker elapsed time plus any
conservative crash reservation, not measured CPU utilization time. Peak observed study process-tree RSS is
125423616 bytes, inside the frozen 8 GiB limit.
Every actual GPU job uses the shared host lease. Admissions reserve the full
bounded worker cost and cannot borrow between study and acceptance categories.

Final cumulative phase charges are baseline 902.574545061 s, screening
6113.346416442 s, ablations 1826.094392481 s, repeatability 70.478730162 s,
and finalists 0 s. Every original campaign/phase cap and prior slice cap remains.
The measured study snapshot has 13044 events and SHA-256
`e07935fdeff4ec071a83b1389868e9922701543c8885b7f541bd90c1a10c5297`. Final acceptance extends it to 13056 events,
SHA-256 `6db55153153e66ed5c2398417d008e4edd278e11153cf87b975345f1a574d34d`. The first 8278 events remain
`c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a`,
with 7015.920961503 seconds consumed before GPUP-6; all older prefixes remain intact.
No reservation remains pending. No budget was reset or augmented beyond ADR-0025.

## Identities and reproduction

- Frozen protocol: `52060731e175f7d8bacd9135559049f9eda598cd79339136fb01b5c6d5d1621e`.
- Measured source tree: `f9711a5fc44d9f9eab9f9d396e61afc660e80742db161901903f9cd89d6ab980`.
- Measured source archive: `39a25ac089da66a50fa6dcc966e922ecfe12d1fff63706181f2a6d5ca3a346aa`.
- Measured executable: `a752fb3e5df5e0c514c9363ef6112d07e74a436bc89062c77fc7d3ba319c452e`.
- Precision kernel (unchanged): `2780f58bf7c6fa506db8ebc7911fa71a512b6417633215820be34d409e702e25`.

Measured source, executable, code objects, frozen inputs, every trial/endpoint,
workers, stdout/stderr, ledger snapshot and `report.json` remain in
`artifacts/gpup6-adaptive-v1`. Acceptance receipts, clean-source check and the
final-verifier receipt remain in `artifacts/gpup6-acceptance`. Raw archives and
binaries are ignored rather than committed. Final validation/archive checks
change no numerical path; the measured archive remains the timing authority.

```sh
python3 tools/benchmark_lp_adaptive.py --dry-run
# Read-only analysis; choose a new output, never overwrite the retained report.
python3 tools/report_lp_adaptive.py --output /tmp/gpup6-reverified.json
```

Execution requires the frozen budget authority and intact prior ledger; a clean
checkout can validate the protocol and synthetic budget tests without those local
artifacts. Existing attempted identities are never retried. New measurements
need a separately authorized protocol identity, never a ledger reset. The
[operations guide](../operations/lp-precision.md#adaptive-fp32fp64-recovery)
explains invocation and accounting.
