# GPUP-2: Certified LP Baseline Costs

Purpose: record the completed development baseline and its limits. Owner: numerical
backend and experiment tooling. Status: measured 2026-09-15; Slice 2 accepted with
exact acceptance coverage in [active task](../../state/active-task.md).
Protocol: [SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md) and
[ADR-0014](../decisions/ADR-0014-lp-baseline-protocol.md).

## Findings

All 144 planned trials completed as recorded attempts: 108 primary timings and
36 separate profiles across 12 development instances and three implementations.
The existing GPU backend certified 6/36 primary trials, covering only the two
small witness instances. Host LP certified 27/36; pinned HiGHS 1.11.0 certified
30/36. This baseline establishes no GPU latency advantage at the selected targets.
Failures remain part of coverage; completed measurement does not mean every LP solved.

Profiles identify host certification and GPU context creation as substantial costs.
The host adapts restart anchors and primal weight; the GPU holds its initial
anchors and weight fixed. These controller differences affect iteration counts
and convergence. GPUP-3 must create the shared resumable FP64 control before
GPUP-4 evaluates residency or kernel optimizations. No controller, arithmetic,
solver default, tolerance, seed or split changed for these measurements.

## Primary timing and coverage

Each cell is the median fresh-process elapsed time in milliseconds over three
attempts, followed by the common outcome. C = independently certified success;
W = 50,000-iteration limit, with no feasible endpoint; T = deadline timeout;
F = backend failure. All three repetitions had the same outcome in each cell.
T and W times describe observed execution, not estimated time to a solution;
time to certified success is censored or unavailable.

| Development instance | HiGHS ms | Host LP ms | CUDA LP ms |
| --- | ---: | ---: | ---: |
| scheduling-20x5 | 55.967 C | 3144.609 C | 3037.588 W |
| scheduling-50x10 | 2272.258 C | 10138.180 T | 10190.245 T |
| irregular-256 | 31.773 C | 208.063 C | 2188.055 W |
| irregular-2048 | 10093.288 T | 1902.161 C | 9228.422 W |
| dense_block-256 | 27.275 C | 219.161 C | 2235.548 W |
| dense_block-1024 | 138.472 C | 997.158 C | 5370.539 W |
| scaling-64 | 11.296 C | 136.891 C | 1501.805 W |
| scaling-256 | 109.255 F | 740.608 C | 2187.509 W |
| small-4 | 7.226 C | 6.979 C | 420.530 C |
| small-16 | 7.205 C | 11.625 C | 451.040 C |
| ta001-relaxation | 62.523 C | 10052.019 T | 3002.247 W |
| ta011-relaxation | 136.591 C | 10082.357 T | 3446.357 W |

Host and GPU deadline cases retained interruption evidence. HiGHS irregular-2048
reached the deadline with a numerically rejected candidate; scaling-256 returned
a backend failure without a certificate. There were no study fallbacks, unsupported
executions, invalid sidecars, missing trials or memory-watchdog terminations.
Fallback is covered separately by the leased acceptance fixture and remains an
explicit requested/executed-backend distinction.

Primary timing covers process launch through input preparation, solving,
independent original-model checks, evidence serialization and process teardown.
The additional standalone verifier cost is reported separately: 24.459310130 CPU
seconds across all trials. Queue wait is excluded from solve latency and charged
GPU time; all 48 GPU jobs together waited 0.000817296 seconds for the lease.

### Paired uncertainty

Ratios are median baseline latency divided by median CUDA latency, using only
mutually certified repetition pairs. A ratio below one favors the CPU baseline.
Intervals use 10,000 paired bootstrap resamples, seed 17002, percentile 95% limits.

| Instance | Baseline / CUDA | Pairs | Ratio | 95% interval |
| --- | --- | ---: | ---: | --- |
| small-4 | highs/cuda-lp | 3 | 0.0172 | [0.0142, 0.0175] |
| small-4 | host-lp/cuda-lp | 3 | 0.0166 | [0.0140, 0.0226] |
| small-16 | highs/cuda-lp | 3 | 0.0160 | [0.0154, 0.0246] |
| small-16 | host-lp/cuda-lp | 3 | 0.0258 | [0.0250, 0.0267] |

The other ten instances have zero mutually certified pairs, so their ratios
and intervals are unavailable. Three repeats give very weak variability evidence:
bootstrap samples contain only three observed pairs and do not support broad
generalization. The small witness cases start at a constructed optimum and mainly
measure startup/check overhead; they do not demonstrate iterative convergence.

## Separate profiles, work and memory

Profiles are separate executions and never enter primary ratios. Existing
synchronization boundaries delimit device phases; primary executions acquire no
additional synchronization for profiling. Representative CUDA observations:

| Instance | Context ms | Host checks ms | Kernels + synchronization ms | Iterations / launches | LP buffer bytes |
| --- | ---: | ---: | ---: | --- | ---: |
| small-4 | 370.176 | 0.169 | 3.064 | 200 / 1200 | 680 |
| scaling-64 | 368.646 | 230.113 | 805.517 | 50000 / 300000 | 36,896 |
| dense_block-1024 | 306.787 | 3822.363 | 1029.134 | 50000 / 300000 | 933,896 |
| irregular-2048 | 392.372 | 7299.770 | 1234.591 | 50000 / 300000 | 1,125,248 |
| scheduling-50x10 | 391.840 | 8533.705 | 998.766 | 40592 / 243552 | 1,627,768 |

GPU context setup spans 306.8–433.9 ms across the twelve profiles. On irregular-2048,
host checks took 7.300 s versus 1.235 s for kernels plus synchronization. Host LP
certified that instance at 1,400 iterations and six restarts, whereas GPU LP used
50,000 iterations without a feasible endpoint. These are measured costs for different
controllers. Removing host authority or inferring a pure device speedup would not
follow from this evidence.

For small-4, kernels plus synchronization took 3.064 ms and context creation
370.176 ms; fresh-process CUDA median latency was 420.530 ms. For scaling-64,
kernels plus synchronization was the largest measured phase at 805.517 ms.
Residency optimization remains a later experiment; small explicit buffers alone
do not establish its expected benefit.

Counters record six successful kernel launches per completed GPU iteration.
The interrupted scheduling-50x10 profile performed 40,592 iterations while its
last assessment and dual witness belonged to iteration 40,400. This distinction
is preserved in evidence. HiGHS work is its native simplex iteration count;
internal native phases and restart counts are unavailable, with a recorded reason.
FP64 is fixed by this version-1 configuration grid. Quantization, precision
changes, precision audits and recovery retries are inapplicable, recorded as zero.

Raw profiles also retain input preparation, preconditioning, invariant allocation
and upload, working allocation/upload, readback, independent endpoint checking
and solve-record serialization. Startup, sidecar output and teardown that lack
separate clocks remain included in whole-process timing. Host phases are measured
on the host; device phases are wall time including synchronization, not CUDA event
kernel-only timings. Fallback costs are inapplicable in this campaign.

| Requested backend | Maximum sampled process-tree RSS bytes, all runs |
| --- | ---: |
| highs | 62,705,664 |
| host-lp | 28,229,632 |
| cuda-lp | 125,726,720 |

The 10 ms RSS watchdog can miss brief peaks and double-count shared pages.
Very short CPU jobs can have incomplete RSS samples; these are not exact peaks.
Maximum explicit CUDA LP buffer allocation was 1,627,768 bytes, including empty
buffer padding. Driver/context residency is excluded from that counter and recorded
in device telemetry. CUDA virtual-address reservations are not resident memory.
Both 8 GiB limits remained untriggered.

### Certificate quality

Every accepted sidecar was checked again by the standalone Rust verifier against
the original model. The small GPU successes had zero conservative gap and zero
outward allowance. Across certified profiles, the largest gap upper bound was
8.449e-7 for host LP and 2.831e-7 for HiGHS; these close under the frozen combined
absolute/relative 1e-9 targets at their objective scales. The corresponding maximum
outward allowances across certified profiles were 2.831e-7 and 8.196e-8.
HiGHS profiles required 278 total multiplier repairs across the ten certified
instances; each was re-certified conservatively. Raw sidecars retain all individual
allowances, gaps, repair counts, witnesses and refusals.

Native optimal status and native best_bound never establish success here. The
[legacy HiGHS LP bound diagnostic](../../state/known-failures.md#legacy-highs-lp-best_bound-is-not-independent-certificate-evidence)
remains a separate adapter issue. Independent exact-rational GPUP-1 regressions
remain the numerical regression authority; measured agreement is not their replacement.

## Environment and budget

- Intel Xeon Platinum 8457C; one allowed CPU core (0), one solver thread.
- RTX 5090 GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48; driver 580.105.08.
- Linux 5.19.0-32-generic; Rust/Cargo 1.93.1; release build; HiGHS 1.11.0.
- GPU study consumption: **173.148261443 seconds**, including all 48 timing/profile
  jobs from lease acquisition through teardown; allowance 900 seconds.
- CPU-only study jobs: **202.666858567 seconds**, plus verifier cost above.
- Remaining baseline phase: **1,626.851738557 seconds** of 1,800.
- Remaining campaign total: **28,626.851738557 seconds** of 28,800; other phase
  allocations remain 7,200 / 7,200 / 9,000 / 3,600 seconds.
- GPU acceptance was separate: **29.981850548 seconds** of 1,800. CPU acceptance
  gates ran sequentially with GPU acceptance, with four build jobs and a 3,600-second cap.

The campaign paused twice when the prelaunch activity check detected nonzero
utilization, then resumed on the same UUID and ledger after idle telemetry.
No attempted trial was repeated. Before/after telemetry was available for all GPU
jobs; these point samples do not prove thermal stationarity or continuous isolation
from unrelated host activity. Validation and held-out models were generated and
hash-validated, with no solve outcomes observed.

## Raw evidence and reproduction

Large outputs remain ignored under artifacts/gpup-baseline-v1. The canonical
ledger is artifacts/lp-campaign-ledgers/gpup-baseline-v1/ledger.jsonl; a matching
snapshot accompanies the raw bundle. The summary indexes every raw trial by hash,
and each trial hashes its endpoint, worker record, stdout and stderr.

| Artifact | SHA-256 |
| --- | --- |
| benchmarks/configs/lp-campaign-v1.json | `a65d0ac2ce2b2676453d0e15752f887af1ee759318bed8b4538ae3f6f0cf137f` |
| summary.json | `c57de898e75b5c422efd09ed3590e8e9d39f97f2b50ce99535f63d1c41a6cc63` |
| report.md | `52e096f5a3c3f1b84a1a56fef1443742211acc7a91fd5de3d71e63c8cd061385` |
| ledger.jsonl | `aee3f1398725fedf8ad37d644c8960156b897b3a11478839359def4619eb8e37` |
| execution.json | `462fa2906348e140ce3229fb021b8b2345525947b8fc84e09514a690af8988d1` |
| source.tar | `fb927c411b9b1c71bc868691a6d25fa4a855c4df0e3bf2e3e283e3ef16eac104` |

Measured base revision: `6a400cdfafab0f360cb7c8ac545a650a247c70be` with a dirty tree.
Exact measured source-tree SHA-256: `657d7c8c43069a37d9de8e7794f4419a68ac22acd4d45e824c2989fdad78e8d4`.
The source.tar snapshot preserves that tree. Final reporting/state edits,
streamed file hashing, and supervisor signal-history/orphan-reaping hardening
followed measurement; all original trial files remain unchanged. The measured
workload creates no child processes and no campaign trial required forced killing. Solver binary SHA-256: `9538f9b16f1fdf3e224674a9c2e4f76f5e797022f730f858eaf63d2080b048fb`.
LP code-object SHA-256: `6a4c87550f7efec3ff2b29e247e604aac42d8cff83fa42f438d3823d15580f5e`.
HiGHS archive SHA-256: `cea1d1005995e8c8155dd8188c0b959dd2dd42722986158bc16c7fe5f6c1d243`.

```bash
python3 tools/lp_generate.py
bash tools/check.sh
cargo build --release --workspace --locked
python3 tools/benchmark_lp.py --dry-run
python3 tools/benchmark_lp.py --output artifacts/gpup-baseline-v1
python3 tools/lp_report.py --input artifacts/gpup-baseline-v1
```

See [study operations](lp-precision-study.md) for provisioning, endpoint verification
and device acceptance commands. To repeat the measured implementation exactly,
use the archived source tree with the recorded toolchain/native/code objects.
Timing values will vary. The completed local campaign must not be relaunched or
its ledger deleted to manufacture fresh samples. Resume only preserves prior
attempts; changed source/configurations require a recorded experiment migration
carrying forward all 173.148261443 GPU seconds. GPUP-3 is the next bounded task,
and SPEC-0012 must be accepted before its numerical behavior.
