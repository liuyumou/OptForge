# FP32 LP Comparisons and COPT Controls: GPUP-5

Purpose: measure explicit storage, product, accumulation and working-state precision under original-model certification.
Owner: numerical backend and experiment tooling.
Status: complete verified development study, 2026-09-16.
Contracts: [ADR-0019](../decisions/ADR-0019-fp32-lp-comparisons.md),
[SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md),
[SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md).

## Findings

All **480 planned attempts have independently verified endpoints**, including every
failure and timeout. Matched, existing tuned and precision FP64 each certify
**27/36 timing runs**. FP32 storage, products, accumulation and FP64-master correction
certify **12/36**; FP32 working state with correction certifies **6/36**.
COPT CPU PDLP certifies **27/36**, COPT GPU PDLP **24/36**, host LP **27/36**, and
HiGHS **30/36**. All 40 COPT GPU attempts affirmatively report GPU PDLP execution.

FP32 matrix values halve matrix-value storage, but total buffers shrink less because
indices, guards, scratch, bounds and objective data retain their widths. On
irregular-256, precision buffers fall from 143960 to 108264 bytes; FP32 working
state reduces them further to 104168 bytes. These savings do not establish a speed
or convergence improvement. No lower-precision paired latency interval lies wholly
above one against precision FP64. Fixed correction adds work and transfers, and does
not recover the lost coverage. **No supported preset is selected.** Matched remains
the general reference. Adaptive audits and recovery belong to GPUP-6.

## Frozen protocol and timing boundary

Twelve configurations use three timing repetitions on the same twelve development
instances (432 attempts), then one profile on small-4, irregular-256,
irregular-2048 and dense_block-1024 (48 attempts). The grid has 360 GPU and 120 CPU
attempts. Seeds remain 17/17001/17002, absolute/relative targets 1e-9, one CPU
thread and affinity [0], 50000 physical iterations, checks every 200, unchanged
preconditioning/restart/weight settings, a ten-second process deadline, two-second
cleanup, and 8 GiB host RSS/device-buffer limits. Validation and held-out partitions
remain untouched. Profile runs do not enter primary timing comparisons.

All GPU jobs use the shared host-wide lease on RTX 5090
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48, driver 580.105.08, with an Intel Xeon
Platinum 8457C host. CPU acceptance, device acceptance, sanitizers and study work
run sequentially. The archived matched binary and original code object retain
their old identity. Precision uses a separately provisioned code object and the
same conservative step policy in its FP64 comparison; existing controls are unchanged.

Primary elapsed time includes fresh process creation, input preparation, device or
COPT environment setup, iteration, original-model certification, endpoint output
and teardown. Independent re-verification runs afterward and has its own counter.
COPT additionally includes Python/binding startup and a Rust witness-certification
child. Thus these compare complete supported study paths, not bare solver kernels.
CUDA profile phases include host launch/synchronization costs. RSS is a sampled
process-tree estimate; explicit LP buffers exclude CUDA context/driver memory.

COPT 8.0.6 uses isolated bundled Python 3.11 bindings, LpMethod=6, GPUMode=0/1,
GPUDevice=0, Threads=1, Crossover=0 and explicit time/accuracy parameters. Only the
selected UUID is visible to its GPU child. The [COPT parameter reference](https://guide.coap.online/copt/en-doc/parameter.html#gpumode)
documents that requested GPU execution may fall back to CPU; the report checks an
actual PDLP GPU-start log. Native status never establishes success. COPT exposes
no public PDLP iteration-limit or seed setting in this installation: every witness
records that limitation, and counts above 50000 are work-limited even if native
status is optimal. Its iteration allowance is therefore observed, not identically
enforced internally. The hard process deadline applies to all configurations.

The adapter preserves original coefficient values, row/variable bounds, objective
sense and offset. Finite bounds beyond COPT's infinity sentinel are refused. Final
import hardening also refuses nonzero coefficients at or below the documented
1e-10 input threshold, so they cannot silently disappear. Every frozen nonzero
coefficient exceeds that threshold (minimum 9.5367431640625e-7); the added refusal
does not change any measured model. License files remain in the local installation.

## Certified coverage

Counts are timing successes out of 36 and profile successes out of four. The last
column retains all unsuccessful endpoints, including censored process outcomes.

| Configuration | Timing /36 | Profile /4 | Unsuccessful outcomes /40 |
| --- | --- | --- | --- |
| Matched | 27 | 4 | 9 completed/work_limit |
| Tuned FP64 | 27 | 4 | 9 completed/work_limit |
| Precision FP64 | 27 | 4 | 9 completed/work_limit |
| Storage FP32 | 12 | 2 | 26 completed/work_limit |
| Products FP32 | 12 | 2 | 26 completed/numerical_rejection |
| Accumulation FP32 | 12 | 2 | 26 completed/numerical_rejection |
| Master + correction32 | 12 | 2 | 26 completed/numerical_rejection |
| Working FP32 + correction32 | 6 | 1 | 22 completed/numerical_rejection; 11 completed/work_limit |
| Host LP | 27 | 4 | 3 completed/work_limit; 6 timeout/interrupted |
| HiGHS | 30 | 3 | 3 completed/backend_failure; 4 timeout/numerical_rejection |
| COPT CPU PDLP | 27 | 4 | 3 completed/feasible_unclosed; 3 completed/work_limit; 3 timeout/work_limit |
| COPT GPU PDLP | 24 | 4 | 3 completed/feasible_unclosed; 3 completed/numerical_rejection; 6 completed/work_limit |

## Certified timing medians

Seconds, using successful repetitions only. A dash means no certified repetition;
it is not a fast solve. Every nonempty cell below has three certified repetitions.
Failures remain in the coverage table and raw elapsed-time records.

| Instance | Matched | Tuned FP64 | Precision FP64 | Storage FP32 | Products FP32 | Accumulation FP32 |
| --- | --- | --- | --- | --- | --- | --- |
| scheduling-20x5 | 0.589 | 0.521 | 0.581 | — | — | — |
| scheduling-50x10 | — | — | — | — | — | — |
| irregular-256 | 0.304 | 0.305 | 0.319 | 0.317 | 0.315 | 0.320 |
| irregular-2048 | 0.474 | 0.422 | 0.506 | — | — | — |
| dense_block-256 | 0.345 | 0.323 | 0.341 | 0.332 | 0.373 | 0.332 |
| dense_block-1024 | 0.417 | 0.407 | 0.446 | — | — | — |
| scaling-64 | 0.363 | 0.322 | 0.340 | — | — | — |
| scaling-256 | 0.395 | 0.383 | 0.424 | — | — | — |
| small-4 | 0.294 | 0.291 | 0.278 | 0.288 | 0.291 | 0.291 |
| small-16 | 0.308 | 0.329 | 0.271 | 0.299 | 0.310 | 0.294 |
| ta001-relaxation | — | — | — | — | — | — |
| ta011-relaxation | — | — | — | — | — | — |

| Instance | Master + correction32 | Working FP32 + correction32 | Host LP | HiGHS | COPT CPU PDLP | COPT GPU PDLP |
| --- | --- | --- | --- | --- | --- | --- |
| scheduling-20x5 | — | — | 2.669 | 0.056 | 0.362 | 0.842 |
| scheduling-50x10 | — | — | — | 2.278 | — | — |
| irregular-256 | 0.340 | — | 0.186 | 0.032 | 0.299 | 0.638 |
| irregular-2048 | — | — | 1.672 | — | 0.416 | 0.792 |
| dense_block-256 | 0.351 | — | 0.196 | 0.025 | 0.291 | 0.645 |
| dense_block-1024 | — | — | 0.873 | 0.130 | 0.373 | 0.752 |
| scaling-64 | — | — | 0.124 | 0.011 | 0.273 | 0.645 |
| scaling-256 | — | — | 0.655 | — | — | — |
| small-4 | 0.279 | 0.298 | 0.007 | 0.007 | 0.267 | 0.639 |
| small-16 | 0.324 | 0.299 | 0.011 | 0.007 | 0.270 | 0.640 |
| ta001-relaxation | — | — | — | 0.055 | 0.683 | — |
| ta011-relaxation | — | — | — | 0.135 | — | — |

## Paired latency and uncertainty

Ratios are precision-FP64/candidate medians on mutually certified repetitions;
values above one favor the candidate. Each estimate uses three paired repetitions,
10000 bootstrap resamples and seed 17002. These are unadjusted development
intervals, with neither held-out evidence nor a multiple-comparison claim.

| Instance | Candidate | Ratio | 95% interval |
| --- | --- | --- | --- |
| irregular-256 | Storage FP32 | 1.0076 | [0.9793, 1.0200] |
| irregular-256 | Products FP32 | 1.0127 | [0.9397, 1.0213] |
| irregular-256 | Accumulation FP32 | 0.9969 | [0.9408, 1.0070] |
| irregular-256 | Master + correction32 | 0.9391 | [0.8361, 0.9675] |
| dense_block-256 | Storage FP32 | 1.0258 | [0.9123, 1.0315] |
| dense_block-256 | Products FP32 | 0.9137 | [0.8903, 1.0613] |
| dense_block-256 | Accumulation FP32 | 1.0262 | [0.8635, 1.0616] |
| dense_block-256 | Master + correction32 | 0.9699 | [0.8073, 1.0738] |
| small-4 | Storage FP32 | 0.9656 | [0.8835, 1.1474] |
| small-4 | Products FP32 | 0.9557 | [0.9218, 1.1076] |
| small-4 | Accumulation FP32 | 0.9564 | [0.8110, 1.1890] |
| small-4 | Master + correction32 | 0.9956 | [0.9956, 1.1050] |
| small-4 | Working FP32 + correction32 | 0.9323 | [0.8679, 1.0817] |
| small-16 | Storage FP32 | 0.9070 | [0.9070, 0.9759] |
| small-16 | Products FP32 | 0.8759 | [0.8692, 1.1046] |
| small-16 | Accumulation FP32 | 0.9217 | [0.8667, 1.0506] |
| small-16 | Master + correction32 | 0.8383 | [0.8383, 0.8744] |
| small-16 | Working FP32 + correction32 | 0.9070 | [0.8963, 0.9991] |

The report also retains all matched/candidate comparisons. COPT's paired
end-to-end ratios below include its setup and witness path, as defined above.

| Instance | Matched / COPT CPU | 95% interval | Matched / COPT GPU | 95% interval |
| --- | --- | --- | --- | --- |
| scheduling-20x5 | 1.6257 | [1.5408, 1.7103] | 0.6992 | [0.6787, 0.6992] |
| scheduling-50x10 | — | — | — | — |
| irregular-256 | 1.0166 | [1.0054, 1.1389] | 0.4764 | [0.4722, 0.5364] |
| irregular-2048 | 1.1394 | [1.0036, 1.2871] | 0.5981 | [0.5298, 0.6767] |
| dense_block-256 | 1.1879 | [1.1515, 1.2016] | 0.5358 | [0.5194, 0.5407] |
| dense_block-1024 | 1.1200 | [1.0335, 1.1637] | 0.5552 | [0.5420, 0.5724] |
| scaling-64 | 1.3287 | [1.1907, 1.3787] | 0.5620 | [0.5020, 0.5832] |
| scaling-256 | — | — | — | — |
| small-4 | 1.1021 | [1.0910, 1.1723] | 0.4608 | [0.4316, 0.4934] |
| small-16 | 1.1386 | [1.1045, 1.1590] | 0.4805 | [0.4607, 0.4831] |
| ta001-relaxation | — | — | — | — |
| ta011-relaxation | — | — | — | — |

## Storage, arithmetic and correction costs

These are single profile observations, not additional latency repetitions. P/C
are proposed updates and FP64 corrections; both consume the physical work budget.
Kernel time includes launches and synchronization. An unsuccessful run's cost is
the cost to its reported stop, not time to certification. Memory includes both
matrix orientations, indices, guards, scratch, working state and empty padding;
FP64 saved state is host-owned and contributes to process RSS.

| Instance | Mode | Outcome | Device bytes | P/C | Kernel ms | Correction ms | Max discrepancy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dense_block-1024 | Master + correction32 | numerical_rejection | 688136 | 42079/1314 | 982.778 | 291.767 | 0.05127 |
| dense_block-1024 | Precision FP64 | certified_success | 958472 | 1800/0 | 42.516 | 0.000 | 0 |
| dense_block-1024 | Storage FP32 | work_limit | 688136 | 50000/0 | 1055.724 | 0.000 | 0 |
| dense_block-1024 | Working FP32 + correction32 | work_limit | 671752 | 48485/1515 | 1162.462 | 336.655 | 0.05293 |
| irregular-2048 | Master + correction32 | numerical_rejection | 881240 | 35455/1107 | 1056.491 | 498.853 | 0.08295 |
| irregular-2048 | Precision FP64 | certified_success | 1174400 | 1600/0 | 40.925 | 0.000 | 0 |
| irregular-2048 | Storage FP32 | work_limit | 881240 | 50000/0 | 1281.221 | 0.000 | 0 |
| irregular-2048 | Working FP32 + correction32 | numerical_rejection | 848472 | 41279/1289 | 1248.227 | 587.721 | 0.08783 |
| irregular-256 | Master + correction32 | certified_success | 108264 | 1400/43 | 30.268 | 2.198 | 3.629e-06 |
| irregular-256 | Precision FP64 | certified_success | 143960 | 1400/0 | 26.838 | 0.000 | 0 |
| irregular-256 | Storage FP32 | certified_success | 108264 | 1400/0 | 26.840 | 0.000 | 0 |
| irregular-256 | Working FP32 + correction32 | work_limit | 104168 | 48485/1515 | 1026.991 | 68.951 | 0.07234 |
| small-4 | Master + correction32 | certified_success | 712 | 200/6 | 4.169 | 0.007 | 0 |
| small-4 | Precision FP64 | certified_success | 776 | 200/0 | 3.864 | 0.000 | 0 |
| small-4 | Storage FP32 | certified_success | 712 | 200/0 | 3.856 | 0.000 | 0 |
| small-4 | Working FP32 + correction32 | certified_success | 648 | 200/6 | 4.197 | 0.008 | 0 |

On irregular-256, products and accumulation profiles also use 108264 bytes and
1400 proposals; kernel/synchronization costs are 26.838 and 26.858 ms, versus
26.838 ms for precision FP64. Matrix conversion/norm preparation is about 1.1 ms,
and context setup is 177–208 ms across these precision profiles. The conservative
precision control takes 1400 iterations versus 1200 for the existing tuned control;
that is a declared policy difference, not a storage-only effect.

Fixed master correction there performs 43 additional host steps (2.198 ms), grows
uploads from 141032 to 489192 bytes and readbacks from 286720 to 942080 bytes,
and spends 30.268 ms in launches/synchronization. FP32 working state consumes all
50000 physical steps, with 1515 corrections (68.951 ms), and still does not certify.
On irregular-2048, master correction spends 498.853 ms in 1107 corrections and
stops numerically; the working-state variant spends 587.721 ms in 1289 corrections.
Correction discrepancies are diagnostics, not certificates or audit thresholds.
The fixed policy only recomputes its scheduled last step, not the whole window.

### COPT setup and validation overhead

COPT's retained log reports native solve time rounded to 0.01 seconds. The residual
between whole-process elapsed time and that native time includes binding/license
and model setup, export, Rust certification, process startup and teardown. These
components are charged together; an isolated setup phase is unavailable. Negative
rounding residuals are clamped to zero. The table uses separate profile runs.

| Instance | COPT mode | Whole process ms | Native solve ms (rounded) | Outside native solve ms |
| --- | --- | --- | --- | --- |
| dense_block-1024 | COPT CPU PDLP | 404.766 | 20.00 | 384.766 |
| dense_block-1024 | COPT GPU PDLP | 764.292 | 160.00 | 604.292 |
| irregular-2048 | COPT CPU PDLP | 448.425 | 20.00 | 428.425 |
| irregular-2048 | COPT GPU PDLP | 873.623 | 160.00 | 713.623 |
| irregular-256 | COPT CPU PDLP | 294.378 | 0.00 | 294.378 |
| irregular-256 | COPT GPU PDLP | 628.994 | 130.00 | 498.994 |
| small-4 | COPT CPU PDLP | 269.713 | 0.00 | 269.713 |
| small-4 | COPT GPU PDLP | 621.653 | 120.00 | 501.653 |

## Retained failures and scope

Storage-only FP32 exhausts work on eight timing instances. Product/accumulation
modes hit guarded nonzero-to-zero product loss on those eight instances; the guard
is checked before projection can hide it. Master correction does not prevent those
stops. Working FP32 additionally loses certification on irregular-256 and
dense_block-256. All numerical failures retain their last independently assessed
witnesses and physical/launch accounting; none is converted into precision recovery.

COPT CPU has work-limited scheduling-50x10 and ta011 outcomes, and unclosed
scaling-256 endpoints. COPT GPU additionally has rejected ta001 endpoints. HiGHS
retains four irregular-2048 process timeouts and three scaling-256 run_error
outcomes. Host LP retains six process timeouts and three work-limited attempts.
There are no missing/invalid endpoints, lease failures, runtime fallbacks,
unsettled reservations or execution-identity mismatches in this study.

Acceptance preflights retain an initially incorrect COPT callback and a GPU-log
wording mismatch: this installed version says “using GPU 0”, while another
supported spelling is “on GPU 0”. The corrected parser requires actual PDLP start,
not device discovery. These preflight failures remain in the separate acceptance
ledger and artifacts. No measurement result was replaced or rerun selectively.

## Acceptance and artifact identities

Full pinned-native tools/check.sh passed on the exact measured source; final
source acceptance is recorded in [active task](../../state/active-task.md).
The final regular device suites pass **47 cases** (14 CUDA, six schedule, 27 LP).
All **six precision cases** pass memcheck, racecheck, initcheck and synccheck
sequentially on the same pinned GPU, with zero errors and zero race warnings.
Six precision CLI solve/replay pairs preserve numerical/control/execution bits;
missing code falls back to pinned HiGHS while preserving the request and failure.
Independent host tests retain GPUP-1 exact-rational authority and legacy FP64
trajectories. Native COPT minimization/maximization fixtures include a ranged row
and objective constant and certify objectives 3.5 and 10.5 independently.

The final device-only boundary fixture and COPT input-range refusal were added
after the frozen run. Runtime kernels and iteration behavior were not changed;
the measured source archive and binary remain available. No claim equates the
final source hash with the measured source hash.

The canonical ledger preserves its complete 1902-event prefix and prior
**902.574545061 seconds**. This slice adds **421.636094192 screening seconds**,
for **1324.210639253 cumulative seconds**, below **4502.574545061**. The campaign's
28800-second cap and original phase caps remain. Separate acceptance uses
**80.458622460 of 900 GPU seconds**, including failed preflights and repeated gates.
Four build jobs were used within the four-hour CPU validation ceiling.

Ignored raw evidence is retained under artifacts/gpup5-fp32-v1; the complete
artifact-index.json hashes trials, raw streams, logs, witnesses, source archive,
configuration identities, executable, code objects and computed report. Acceptance
logs are under artifacts/gpup5-acceptance. Reproduce verification with
`python3 tools/report_lp_precision.py`; see [operations](../operations/lp-precision.md).
Local artifacts and licenses are not committed or published.

| Identity | SHA-256 |
| --- | --- |
| Protocol | b40217f3e5ce7260f903b8f16882a14c1fc0521c2c397871240e51d90da7ec48 |
| Canonical ledger | 66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0 |
| Measured source tree | 61d975f8bba041879d79966a79ecc12fb88d69bc44b39ea41801b59c2ef9adfe |
| Measured source archive | 9cbd542195215aba0d485b5a3a77c4f0b9572dfb3fa4f8a35809edf63d0c4323 |
| Measured executable | ae8dea80c603e4136c45ffe78af402f7ae6dc2079e17f1f70838988a7be99470 |
| Precision code object | 2780f58bf7c6fa506db8ebc7911fa71a512b6417633215820be34d409e702e25 |
| COPT library | f4d5280b94dab704dc7fadb8024b8ec947438a364456a4bc5f8b435146729c8c |
| COPT Python binding | cd80baacf015b98d576b15faeb3dd6d359f6d45990aab052f03341ca3786feef |
| Artifact index | ca2465316ec5ae7b8c5d26a610b8ca2ba733e983e931a6b7967550153a0064c6 |
