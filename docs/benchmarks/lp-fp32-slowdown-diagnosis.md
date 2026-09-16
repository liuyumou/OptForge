# Why FP32 Did Not Improve GPUP-5 Solve Time

Status: completed diagnostic follow-up, 2026-09-16. Scope:
[ADR-0020](../decisions/ADR-0020-fp32-latency-diagnosis.md).
The [original 480-attempt study](lp-fp32-gpup5.md) and all its artifacts remain unchanged.

## Findings

The largest loss comes from **additional iterations without reaching the original
model's accuracy target**. The FP32 sparse kernels can be faster, but their savings
are small compared with that extra work. Three separate effects matter:

1. Rounding the scaled matrix perturbs constraints by more than their original
   feasibility allowances. FP32 storage alone loses coverage even with FP64 products,
   accumulation and state. Further product/state rounding adds other errors and
   eventually triggers strict nonzero-to-zero product guards.
2. The experimental precision executor is more expensive than the older tuned
   executor even when both use FP64. It adds guarded arithmetic and conversions,
   retains FP64 vector updates, launches six kernels per update and reads state
   back more frequently. Comparing these two executors is not an isolated FP32 test.
3. Fixed host correction adds transfers and CPU work. It replaces one scheduled
   update, not the preceding 31 updates, and does not restore the lost coverage.

On equal work, uncorrected FP32 differs little from precision FP64 on small-4 and
irregular-256, saves about 1–2% on irregular-2048, and has mixed results on
dense_block-1024: storage/accumulation save about 13%/15%, while FP32 products with
FP64 accumulation cost about 3% more. There is no general finding that FP32
arithmetic itself is slower. None of these short runs establishes faster time to
a certified solution.

## Measurement boundaries and completeness

All **213 frozen GPU jobs** ran once on the original RTX 5090 UUID under the shared
host lease: 196 untraced profiled short runs, 14 Nsight Systems traces and three
Nsight Compute attempts. Each produced an independently verified endpoint and
exactly 200 proposals. Correction modes additionally charged six host steps, for
206 physical steps. The intended work-limit exit code 1 is retained and is eligible
for equal-work timing; numerical errors and incomplete work are not.

Seven randomized blocks per instance use the original order seed 17001, solve seed
17, one CPU thread/core, 1e-9 targets, preconditioner/controller settings, separate
kernels and unchanged code objects. Only the explicit diagnostic work limits differ
from GPUP-5. Four development profile instances were used; validation and held-out
partitions were untouched. No warmups, selective repeats, runtime changes, altered
guards or tolerance changes were made. CPU acceptance and GPU measurement ran
sequentially, with four build jobs and a two-hour CPU validation ceiling.

The short runs examine the first 200 updates, not the entire late convergence or
subnormal regime. Primary solve-time conclusions still come from GPUP-5. Traced
kernel durations are instrumented observations, excluded from untraced medians.
The CUDA launch API can overlap GPU execution; their times must not be added.

All 14 raw traces decoded offline and all match their endpoint's **1200 launches**.
Automatic import initially failed because libdw.so.1 was absent from the importer's
library path. Existing private GPUP-2 libraries decoded the saved streams without
rerunning any GPU work. All three hardware-counter attempts returned
**ERR_NVGPUCTRPERM**. These are unsuccessful counter collections despite valid solver
endpoints; no driver policy was changed. Therefore cache-hit rates, achieved
bandwidth, occupancy and limiting arithmetic pipelines remain unmeasured. NVIDIA's
[profiling guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#replay)
also explains that counter replay adds work; such durations would not be primary
timing evidence even if collection had succeeded.

## Equal proposed work

Median microseconds per proposed update, seven runs per cell. This envelope includes
kernel submission/execution/synchronization and dynamic working allocation, uploads
and readback. The latter phases are separately recorded by tuned FP64 but included
inside the precision executor's kernel phase; they are added for the tuned column
to compare the same scope. Initialization, host checks/controller work and correction
are excluded here. Precision comparisons use the common conservative step policy.

| Instance | Tuned FP64 | Precision FP64 | Storage FP32 | Products FP32 | Accumulation FP32 | Master + correction32 | Working FP32 + correction32 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small-4 | 15.010 | 19.323 | 19.268 | 19.299 | 19.265 | 20.813 | 20.902 |
| irregular-256 | 14.933 | 19.570 | 19.568 | 19.560 | 19.619 | 21.670 | 21.597 |
| irregular-2048 | 16.988 | 25.753 | 25.411 | 25.246 | 25.238 | 29.775 | 30.434 |
| dense_block-1024 | 15.135 | 24.030 | 20.873 | 24.682 | 20.487 | 23.716 | 24.328 |

Paired ratios below are precision-FP64/candidate medians on the same seven blocks;
above one favors FP32. Intervals use 10000 paired bootstrap resamples and the
existing analysis seed 17002. They are exploratory, unadjusted intervals for this
short-run phase, not claims about full solve latency or other models.

| Instance | Storage ratio [95% interval] | Products ratio [95% interval] | Accumulation ratio [95% interval] |
| --- | --- | --- | --- |
| small-4 | 1.0028 [0.9992, 1.0055] | 1.0012 [0.9992, 1.0044] | 1.0030 [1.0007, 1.0059] |
| irregular-256 | 1.0001 [0.9988, 1.0037] | 1.0005 [0.9966, 1.0036] | 0.9975 [0.9950, 1.0010] |
| irregular-2048 | 1.0135 [1.0047, 1.0312] | 1.0201 [1.0113, 1.0273] | 1.0204 [1.0022, 1.0301] |
| dense_block-1024 | 1.1512 [1.1381, 1.1545] | 0.9736 [0.9710, 0.9763] | 1.1729 [1.1665, 1.1771] |

The storage-to-products comparison on dense_block-1024 is particularly useful:
adding FP32 operand conversion/products while retaining FP64 accumulation increases
this phase from 20.873 to 24.682 microseconds. Changing accumulation to FP32 reduces
it to 20.487. This isolates a real implementation-dependent arithmetic cost. Without
counters or a trace on that instance, attributing the difference to a particular
pipeline or cache would exceed the evidence.

## Convergence dominates the large losses

These observations come from the preserved, full-length GPUP-5 profile runs.
Kernel-phase time includes launch/synchronization. A failed run's time is its cost
to stop, never a successful solution time.

| Instance | Mode | Proposals | Kernel phase, ms | Microseconds/proposal | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| irregular-2048 | Precision FP64 | 1600 | 40.925 | 25.578 | Certified |
| irregular-2048 | Storage FP32 | 50000 | 1281.221 | 25.624 | Work limit |
| irregular-2048 | Products FP32 | 35464 | 907.121 | 25.579 | Product-loss guard |
| irregular-2048 | Accumulation FP32 | 47000 | 1177.887 | 25.061 | Product-loss guard |
| dense_block-1024 | Precision FP64 | 1800 | 42.516 | 23.620 | Certified |
| dense_block-1024 | Storage FP32 | 50000 | 1055.724 | 21.114 | Work limit |
| dense_block-1024 | Products FP32 | 41264 | 993.518 | 24.077 | Product-loss guard |
| dense_block-1024 | Accumulation FP32 | 42128 | 854.138 | 20.275 | Product-loss guard |

Storage FP32 does **31.25 times as many proposals** on irregular-2048 with nearly
identical cost per proposal, and still fails. On dense_block-1024 it does **27.78
times as many proposals** despite cheaper iterations, and still fails. The overall
study certifies 27/36 timing attempts with precision FP64 versus 12/36 with storage,
products, accumulation or master correction, and 6/36 with FP32 working state.

The precision step policy itself is a separate comparison with tuned FP64: on
irregular-2048 the admitted precision step is about 0.343 of the older step; on
dense_block-1024 about 0.331. Precision FP64 uses this same conservative policy.
Thus it cannot explain the FP32 coverage loss relative to that control. The norm
bounds of the represented matrix can cause small additional step differences.

### Exact representation inspection

A CPU-only Rust probe re-verifies original endpoints and exports the actual scaled
operator/preconditioner through existing APIs. Python rational arithmetic then
computes original and represented row activities at archived repetition-zero
witnesses. All **166292 original nonzero coefficients** across the twelve models
are exactly representable in FP32. After FP64 scaling, only **18** remain exactly
representable. Input coefficients being simple integers/dyadics does not prevent
scaled-matrix quantization error.

For an original-coordinate witness x, the implied represented coefficient is
`FP32(Dr A Dc)[i,j] / (Dr[i] Dc[j])`. The diagnostic uses exact rational evaluation
of these stored binary values, original bounds and the original validator's
allowance. It also evaluates the FP64-scaled coefficient divided by the same
scales as a scaling-roundoff control. It is not a certificate for a represented
model, and does not separately model rounding of its scaled bounds.

Concrete examples from storage-FP32 endpoints:

| Instance / row | Original violation | Implied FP32-operator violation | Original allowance | Operator activity shift |
| --- | ---: | ---: | ---: | ---: |
| irregular-2048 / 805, upper | 3.078e-7 | 8.870e-9 | 9.000e-9 | -2.989e-7 |
| dense_block-1024 / 798, lower | 5.996e-7 | 3.531e-8 | 3.800e-8 | +5.643e-7 |
| scheduling-20x5 / 14, upper | 4.385e-8 | 6.056e-9 | 2.000e-9 | -3.780e-8 |

The first two rows meet the allowance under the implied FP32 operator but violate
the original row by **34.2** and **15.8** times its allowance. The FP64-scaled
control preserves those original violations to approximately 1e-15 absolute.
This directly identifies representation bias large enough to defeat certification.
It does not prove every failed model is at a quantization floor: several also have
large residuals under the represented operator. Conversely, a saved witness that
certifies the original model need not be feasible for the perturbed operator.
All 72 endpoint diagnostics, including these contrary cases, are retained.

Product/accumulation failures additionally report guard bit 4: nonzero operands
produced zero, not overflow. This is consistent with tiny decaying components
reaching FP32 product underflow. Gradual underflow is enabled, but it cannot represent
values below the smallest representable result. The strict contract stops rather
than silently accepting this loss. Disabling that guard would change the contract
and would not remove the observed scaled-matrix bias.

## What the GPU and host actually do

The [precision kernels](../../cuda/lp_pdhg_precision/lp_pdhg_precision.cu) retain
FP64 vector-update arithmetic, objectives, bounds and control. The product mode
narrows vector operands, performs a rounded FP32 product and widens its result.
The accumulation mode still passes a double-typed sum through the generic path,
with conversions around FP32 additions and double-width shuffle values. Per-value
range checks and guard reductions remain active. These modes are not a wholesale
replacement of every FP64 instruction with one FP32 instruction.

Static disassembly confirms conversions and both-width arithmetic in the shared
precision sparse entry point. It has 3712 static instructions versus 576 in tuned
spmv_warp32, with runtime-selected paths and compiler-generated expansion. These
are code sizes, not dynamic instruction counts or an attribution of elapsed time.
Both sparse kernels use 40 registers; reported local/stack usage is zero, so the
static resource evidence does not support a register-spill explanation.

One trace per mode on irregular-2048 gives:

| Mode | Mean sparse kernel, us | All kernels busy, ms | First-to-last kernel span, ms | Span outside kernels | Readback calls / bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tuned FP64 | 2.323 | 1.852 | 4.111 | 54.9% | 2 / 32768 |
| Precision FP64 | 5.152 | 3.463 | 5.718 | 39.4% | 12 / 327680 |
| Storage FP32 | 4.726 | 3.292 | 5.633 | 41.6% | 12 / 327680 |
| Products FP32 | 4.935 | 3.375 | 5.692 | 40.7% | 12 / 327680 |
| Accumulation FP32 | 4.574 | 3.231 | 5.700 | 43.3% | 12 / 327680 |
| Master + correction32 | 4.577 | 3.231 | 9.981 | 67.6% | 39 / 1064960 |
| Working FP32 + correction32 | 4.562 | 3.256 | 10.477 | 68.9% | 39 / 851968 |

Every row has 1200 launches: two sparse products, primal and dual updates, and two
state stores per proposal. Four vector kernels remain mostly unchanged across
precision widths. Across the precision modes without correction, host launch API
time totals about 3.96–4.09 ms in these traces. Small-4 sparse kernels are only
2.17–2.28 microseconds, with about 52–53% of the kernel span outside kernels.
This leaves limited opportunity for faster sparse arithmetic to reduce total time.
The gap includes submission, waits, transfers and host work; it is not a pure CPU
utilization metric.

The [precision executor](../../crates/optimizer-lp-cuda/src/precision.rs) reads
guards, primal and dual state after each at-most-64-step chunk. Tuned residency
reads the endpoint at its controller boundary. Precision therefore performs ten
times the readback bytes over these 200 updates. Actual traced GPU copy activity
for uncorrected precision is only 0.044–0.049 ms, while its readback API calls span
about 1.27–1.35 ms: waiting and call boundaries matter more here than the copied
byte count alone. Each precision chunk also allocates host readback vectors and
looks up four kernel handles. These are inspected overhead candidates, not
individually timed causes.

### Correction and setup costs

Median combined iteration-execution plus correction time, for 200 proposals:

| Instance | Precision FP64, ms | Accumulation FP32, ms | Master + correction32, ms | Working FP32 + correction32, ms |
| --- | ---: | ---: | ---: | ---: |
| small-4 | 3.865 | 3.853 | 4.169 | 4.188 |
| irregular-256 | 3.914 | 3.924 | 4.743 | 4.727 |
| irregular-2048 | 5.151 | 5.048 | 9.232 | 9.356 |
| dense_block-1024 | 4.806 | 4.097 | 6.176 | 6.293 |

Six host corrections alone cost about 3.291 ms on irregular-2048. Correction splits
chunks around each scheduled last step and invalidates resident state after adopting
the host endpoint: synchronization count rises from 37 to 88, uploads from 25 to
49, and readbacks from 12 to 39. FP32 working state reduces bytes but still requires
these calls and explicitly rounds the adopted FP64 endpoint for continuation.

In the full archived irregular-2048 master run, 1107 corrections cost 498.853 ms;
it still stops on product loss. Recomputing one last step from an already perturbed
state does not undo the previous window. This explains why the fixed schedule can
cost more without restoring coverage; adaptive recovery was deliberately deferred.

Fresh-process CUDA context setup medians are roughly 200–232 ms across the short
run groups, compared with 3–6 ms for their iteration-execution phases. On
irregular-2048, precision FP64 also spends 11.291 ms preparing the represented
operator/norm bounds and 26.371 ms preconditioning. Startup and host work dilute
small iteration savings and make whole-process differences noisy. They do not
explain the 50000-update failures. Context reuse would measure a different,
repeated-solve workload, outside this study's end-to-end boundary.

## Next changes justified by this evidence

Prioritize the numerical failure first: GPUP-6 should use original-operator audits
and explicit recovery/promotion so an error floor does not consume tens of thousands
of ineffective updates. Keep the original-model certificate and retained failure
accounting. One periodic FP64 update is insufficient evidence of recovery.

Then measure specialized precision kernels, cached handles/reused host buffers,
and lower transfer/synchronization overhead while preserving the bounded guard and
cancellation semantics. Any fusion or residency changes need an explicit accepted
execution contract and new code identity. Hold the numerical policy fixed when
comparing costs. These are proposed experiments, not implemented speedups. The
counter restriction prevents a defensible bandwidth/occupancy diagnosis, and these
small matrices do not establish the benefit available on larger workloads.

No solver code, numerical behavior, defaults, supported preset or GPUP-6 behavior
was changed by this follow-up.

## Evidence, budget and reproduction

Evidence is under artifacts/gpup5-diagnosis-v1: the frozen protocol, measured source
archive/executable and unchanged code objects; all requests, results and endpoints;
raw .qdstrm traces and offline .nsys-rep/.sqlite exports; failed counter logs;
full disassembly/resources; 72 exact-rational row diagnostics; paired analysis and
hash index. Post-measurement analysis hardens provenance, reports unavailable
counters and aligns phase boundaries; the archived measured source remains intact.

Full pinned-native acceptance passed on the measured source (422 Rust tests,
119 Python tests, 78 documentation pages). Final tooling/documentation acceptance
is recorded in [active task](../../state/active-task.md). The diagnostic tests cover
the frozen grid, exact representation arithmetic, original ledger snapshots,
phase boundaries, unavailable counters and intentional work-limit eligibility.
No runtime/device code changed, so additional sanitizer workloads were unnecessary.

All 480 historical endpoints were reverified in a temporary copy, reproducing the
old summary and artifact index byte for byte. Every original indexed artifact and
the complete **2862-event ledger prefix** remain unchanged. The diagnostic adds
**143.056235443 screening GPU seconds**, including failed counter attempts, for
**1467.266874696 cumulative seconds**. This is below the 300-second diagnostic cap
and existing 4502.574545061 cumulative ceiling; global and phase caps remain intact.
All 213 reservations are settled, with no missing job, timeout or fallback. The
separate GPUP-5 acceptance allowance was not used.

| Identity | SHA-256 |
| --- | --- |
| Diagnostic ledger (3288 events) | b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef |
| Preserved GPUP-5 ledger prefix | 66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0 |
| Measured source tree | 09320c2290d23bb6d5fbd04294760da0ecc7f606cb86f3b3f443684fc325c96f |
| Measured source archive | 264bf68a9948a56a6d551c020e2ef792480b10e920212400c0a6cc288b9a0911 |
| Measured executable | 5cd6dd6116918d6b190c271023aff349236896f18290e697141969fa5440c077 |
| Unchanged precision code object | 2780f58bf7c6fa506db8ebc7911fa71a512b6417633215820be34d409e702e25 |

`python3 tools/diagnose_lp_precision.py` checks the 213-job plan without GPU work.
The accepted frozen source's --gpu mode records new measurements under the shared
lease and canonical ledger; it refuses changed source across resume. Do not reset
or rerun the completed study to reproduce the analysis. Use
`python3 tools/analyze_lp_precision_diagnosis.py` on the existing evidence;
--cpu regenerates only the representation diagnostics using the built
optimizer-experiment example lp_precision_diagnose. The failed automatic trace
imports are retained; offline-import.json records the exact successful decoder
commands, library identity and outputs. Licenses and local artifacts are not
committed or published.
