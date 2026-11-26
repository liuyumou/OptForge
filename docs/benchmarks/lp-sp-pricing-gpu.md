# Lean GPU pricing candidate: diagnosis and measured results

This follow-up removes measured overhead from the practical pricing candidate. It preserves the final original-model certificate and exact CPU fallback. The original [completed study](lp-sp-pricing.md) remains historical.

See the [compact evidence](lp-sp-pricing-gpu-results.json), [complete cell table](lp-sp-pricing-gpu-comparison.csv), and [implementation](../../research/lp-sp-pricing/README.md).

## Why the previous GPU path was slower

The retained coupled eight-variable case took 5.131 seconds. Device iterations used 0.329 seconds, while Python exact proposal checking used 2.850 seconds. Its last query obtained no GPU labels and still needed 39 exact CPU auxiliary solves.

The old path repeated rational matrix products, constructed large intermediate witnesses, checked already resolved targets, restarted state for precision escalation, and launched several kernels per iteration. FP32 component cross-products used CUDA cores and FP64 accumulation; they did not exploit tensor cores. The difficult final query also had a convergence problem: its large calibration box amplified dual stationarity error, so more mantissa bits alone did not produce exact negative labels.

## Components removed from the candidate hot path

- FP32/FP4 component decomposition and precision restarts: the selected candidate uses native FP64.
- Repeated GPU state allocation: matrix, transpose, workspaces and events are reused across stages.
- Separate projection launches: small matrices use a persistent kernel; larger matrices use fused products and projections with four row warps per block and replayed CUDA graphs.
- Resolved searches: active indices compact the launch grid, and exact labels also resolve companion targets.
- Full intermediate witness strings and Python Fraction parsing: a native GMP checker returns compact label decisions. It computes the primal product once and skips an unnecessary dual bound.
- Unproductive full passes: a stratified pilot stops after 256 steps if it establishes no exact label, handing the remaining work to the exact CPU oracle.

Diagonal steps use 0.9 divided by absolute row/column sums. Weighted Cauchy–Schwarz bounds the scaled operator norm by 0.9. Zero rows/columns use unit steps. This improves numerical proposals without granting them acceptance authority. Exact final certificates, strict independent checking, resource limits and failure records remain. Historical implementations stay available for differential tests and reproduction.

## Fixed-work diagnostics

Each cell performs 64 target searches at 1,000 steps. The table uses CSR, width 64, and medians of three rotated repetitions. Times are device iteration milliseconds; complete auxiliary timings, dense results and all 108 cells are retained in the compact evidence. Candidate preconditioning changes iterates, so these are equal-step cost comparisons, not equal-convergence speedups.

| Auxiliary | Old FP32×2 | Old FP64 | Lean FP64 |
| --- | ---: | ---: | ---: |
| coupled-first | 22.538 | 16.394 | 8.094 |
| coupled-optimum | 57.346 | 28.686 | 13.093 |
| degenerate-optimum | 106.504 | 45.065 | 21.860 |

On the same 32 raw proposals, Python exact checks took 357.537 ms, native full proofs 65.415 ms, and compact native decisions 25.521 ms (14.01× faster than Python). All decisions match the independent Python checker.

## Development and frozen confirmation

| Development version | Exact certificates | Capped seconds |
| --- | ---: | ---: |
| cpu-ladder-v4 | 14/21 | 88.313 |
| gpu-ladder-v2 | 14/21 | 114.679 |
| gpu-opt-ladder-v1 | 14/21 | 95.190 |
| gpu-opt-ladder-v2 | 14/21 | 99.016 |
| gpu-opt-ladder-v3 | 14/21 | 88.805 |
| gpu-opt-ladder-v4 | 14/21 | 89.580 |

Development uses seed 73011 and ten-second per-case caps. Selection maximizes timely exact certificates, then minimizes capped cost. Held-out seed 88371 was frozen after selection. The fresh comparison has eight models across seven families, three lanes and two cyclic order rotations: 48 cold processes. Every lane gets ten native seconds and twenty process seconds. Complete cost includes common model encoding, cold startup, preparation, solving, output and the separate independent exact/strict audit. Idle observation and supervision settlement remain charged but are outside comparable cost.

| Lane | Timely exact | Timely strict 1e-9 | All-cell complete seconds |
| --- | ---: | ---: | ---: |
| cpu | 16/16 | 6/16 | 46.044 |
| legacy_gpu | 14/16 | 6/16 | 103.108 |
| lean_gpu | 16/16 | 6/16 | 55.230 |

All-cell totals include failures and are descriptive; they do not imply equal certified work. Ratios below include only jointly timely certified model/repetition pairs. Values above one favor the lean GPU candidate.

| Tier | Comparator / lean GPU | Paired models / repetitions | Median ratio | Range |
| --- | --- | ---: | ---: | ---: |
| exact | legacy_gpu / lean_gpu | 7 / 14 | 2.430× | 1.465–2.639× |
| exact | cpu / lean_gpu | 8 / 16 | 0.796× | 0.687–0.964× |
| strict | legacy_gpu / lean_gpu | 3 / 6 | 2.401× | 1.465–2.639× |
| strict | cpu / lean_gpu | 3 / 6 | 0.799× | 0.688–0.964× |

The first dense confirmation repetition illustrates where time was removed. These are internal diagnostic phases, not additive complete-cost components; the device time excludes host transfers and checking. Output size includes the retained final certificate.

| Lane | Device seconds | Exact proposal-check seconds | Auxiliary phase seconds | Response bytes |
| --- | ---: | ---: | ---: | ---: |
| cpu | 0.0000 | 0.0000 | 1.1829 | 2843 |
| legacy_gpu | 0.3291 | 2.8963 | 4.8099 | 21483881 |
| lean_gpu | 0.0136 | 0.1128 | 1.6187 | 5919 |

CPU and lean GPU share compact trace output; improvements from that change are not credited exclusively to GPU arithmetic. The old GPU retains its archived full-trace implementation. All deadlines, missing endpoints, late certificates, unmatched outcomes and regressions remain in the CSV. These small generated cases and two repetitions do not establish broad solver superiority or replace the earlier vendor comparison.

## Correctness and retained operational failures

The final candidate passes 64 dense/CSR/width configurations and 1,680 exact differential proposal comparisons. Tests cover continued state, inactive targets, scalar diagonal-PDHG equations, full and compact exact decisions, malformed inputs and lifetime handling. All four CUDA sanitizer smoke processes pass on both persistent and graph paths. The native proof checker passes ASan/UBSan on 96 cases. Final CPU and documentation results appear in the settled checkpoint.

Three failed GPU admission reservations remain: v2 lost its coordinator (empty cleanup), v3 recorded cleanup_incomplete, and v5 failed an overly strong synthetic-label assertion. The first two preceding causes are unavailable; no GPU OOM attribution is made. All seven exact identities from v3 subsequently exited; an additive read-only cleanup proof and source-bound CPU readmission permit continuation without changing the failed receipt. Sanitizer smoke sizes were reduced while retaining both kernel paths. The synthetic fixture now uses epsilon = 1/(1024N); a regression also checks when opposite-slot label inference is unjustified. The first CPU freeze reservation failed because its accounting query included its own active admission reservation; the corrected future-phase query preserves full failed charges and rejects an unsettled confirmation reservation. No LP had started in that failure. All full failure charges remain.

The study allocation and phase caps are unchanged. The final [settled checkpoint](lp-sp-pricing-gpu-checkpoint.json) records usage, failures and process cleanup. The full literal paper run and billion-nonzero evaluation retain their earlier capacity limitations. No tensor-core, arbitrary-precision GPU, or strongly polynomial runtime claim is made.
